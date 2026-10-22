"""Subscriptions, mock checkout and provider webhooks.

``MockBillingProvider`` stands in for Stripe/Paddle/SSLCommerz: it creates
checkout sessions, and "completing" one emits a signed webhook event through
the same code path a real provider would hit, so the webhook handler, signature
verification and idempotency are exercised end to end without external calls.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AppContext
from app.core.plans import PLAN_ORDER, PLANS, get_plan
from app.core.security import new_opaque_token, sign_payload, verify_signature
from app.models import BillingEvent, CheckoutSession, Organization, Subscription, User
from app.services.audit_service import AuditService
from app.services.entitlements import Entitlements
from app.services.errors import Conflict, NotFound, ServiceError, Unauthorized

log = logging.getLogger("app.billing")
PERIOD_DAYS = 30


@dataclass
class SignedEvent:
    body: bytes
    timestamp: str
    signature: str


class MockBillingProvider:
    """Clearly a stub: no money moves. Produces provider-shaped, HMAC-signed events."""

    name = "mock"

    def __init__(self, secret: str, clock) -> None:  # type: ignore[no-untyped-def]
        self.secret = secret
        self.clock = clock

    def checkout_url(self, frontend_url: str, session_id: str) -> str:
        return f"{frontend_url}/dashboard/billing/checkout?session={session_id}"

    def sign(self, event: dict) -> SignedEvent:
        body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
        ts = str(int(self.clock.now().timestamp()))
        return SignedEvent(body=body, timestamp=ts, signature=sign_payload(self.secret, body, ts))

    def event(self, type_: str, data: dict) -> dict:
        return {
            "id": f"evt_{new_opaque_token(12)}",
            "type": type_,
            "created": int(self.clock.now().timestamp()),
            "data": data,
        }


class BillingService:
    def __init__(self, db: AsyncSession, ctx: AppContext) -> None:
        self.db = db
        self.ctx = ctx
        self.audit = AuditService(db, ctx)
        self.entitlements = Entitlements(db)
        self.provider = MockBillingProvider(ctx.settings.billing_webhook_secret, ctx.clock)

    # ------------------------------------------------------------ reads
    async def subscription(self, org: Organization) -> Subscription:
        res = await self.db.execute(select(Subscription).where(Subscription.org_id == org.id))
        sub = res.scalar_one_or_none()
        if sub is None:
            sub = Subscription(
                org_id=org.id, plan=org.plan, status="active", provider="mock", seats=1
            )
            self.db.add(sub)
            await self.db.flush()
        return sub

    async def overview(self, org: Organization) -> dict:
        sub = await self.subscription(org)
        plan = get_plan(org.plan)
        return {
            "subscription": sub,
            "plan": plan.to_dict(),
            "usage": await self.entitlements.usage(org),
            "features": plan.features,
            "plans": [PLANS[p].to_dict() for p in PLAN_ORDER],
        }

    # ------------------------------------------------------------ checkout
    async def create_checkout(
        self, org: Organization, actor: User, plan_id: str, *, ip: str = ""
    ) -> CheckoutSession:
        if plan_id not in PLANS or plan_id == "free":
            raise ServiceError("choose a paid plan", code="invalid_plan")
        if plan_id == org.plan:
            raise Conflict(
                f"organization is already on the {get_plan(plan_id).name} plan", code="same_plan"
            )
        session = CheckoutSession(
            org_id=org.id,
            plan=plan_id,
            status="open",
            created_by=actor.id,
            created_at=self.ctx.clock.now(),
        )
        self.db.add(session)
        await self.db.flush()
        await self.audit.record(
            action="billing.checkout_started",
            org_id=org.id,
            actor=actor,
            target_type="checkout",
            target_id=session.id,
            metadata={"plan": plan_id},
            ip=ip,
        )
        return session

    def checkout_url(self, session: CheckoutSession) -> str:
        return self.provider.checkout_url(self.ctx.settings.frontend_url, session.id)

    async def get_checkout(self, org: Organization, session_id: str) -> CheckoutSession:
        session = await self.db.get(CheckoutSession, session_id)
        if session is None or session.org_id != org.id:
            raise NotFound("checkout session not found")
        return session

    async def complete_checkout(self, org: Organization, session_id: str) -> Subscription:
        """Simulates the customer paying on the provider page: emits ``checkout.completed``."""
        session = await self.get_checkout(org, session_id)
        if session.status != "open":
            raise Conflict(f"checkout session is {session.status}")
        event = self.provider.event(
            "checkout.completed",
            {
                "session_id": session.id,
                "org_id": org.id,
                "plan": session.plan,
                "customer_id": f"cus_{org.id[:12]}",
                "subscription_id": f"sub_{session.id[:12]}",
            },
        )
        signed = self.provider.sign(event)
        await self.handle_webhook(signed.body, signed.timestamp, signed.signature)
        return await self.subscription(org)

    async def cancel(self, org: Organization, actor: User, *, ip: str = "") -> Subscription:
        sub = await self.subscription(org)
        if sub.plan == "free":
            raise Conflict("the free plan cannot be canceled", code="free_plan")
        sub.cancel_at_period_end = True
        sub.canceled_at = self.ctx.clock.now()
        await self.audit.record(
            action="billing.cancel_scheduled", org_id=org.id, actor=actor, ip=ip
        )
        return sub

    async def resume(self, org: Organization, actor: User, *, ip: str = "") -> Subscription:
        sub = await self.subscription(org)
        if not sub.cancel_at_period_end:
            raise Conflict("subscription is not scheduled for cancellation")
        sub.cancel_at_period_end = False
        sub.canceled_at = None
        await self.audit.record(action="billing.resumed", org_id=org.id, actor=actor, ip=ip)
        return sub

    # ------------------------------------------------------------ webhooks
    async def handle_webhook(self, body: bytes, timestamp: str, signature: str) -> BillingEvent:
        secret = self.ctx.settings.billing_webhook_secret
        if (
            not timestamp
            or not signature
            or not verify_signature(secret, body, timestamp, signature)
        ):
            raise Unauthorized("invalid webhook signature", code="bad_signature")
        now = self.ctx.clock.now()
        try:
            if abs(now.timestamp() - int(timestamp)) > 300:
                raise Unauthorized("webhook timestamp outside tolerance", code="stale_webhook")
        except ValueError:
            raise Unauthorized("invalid webhook timestamp", code="bad_signature") from None
        try:
            payload = json.loads(body)
            event_id, type_, data = payload["id"], payload["type"], payload.get("data", {})
        except (ValueError, KeyError):
            raise ServiceError("malformed webhook payload", code="bad_payload") from None

        existing = await self.db.execute(
            select(BillingEvent).where(BillingEvent.event_id == event_id)
        )
        record = existing.scalar_one_or_none()
        if record is not None:
            return record  # idempotent: already processed (or recorded as failed)
        record = BillingEvent(
            provider=self.provider.name,
            event_id=event_id,
            type=type_,
            org_id=data.get("org_id"),
            payload=payload,
            received_at=now,
        )
        self.db.add(record)
        await self.db.flush()
        try:
            await self._apply(type_, data, now)
            record.processed = True
        except ServiceError as exc:
            record.error = exc.detail
            log.warning("webhook %s (%s) not applied: %s", event_id, type_, exc.detail)
        return record

    async def _apply(self, type_: str, data: dict, now: datetime) -> None:
        org_id = data.get("org_id")
        org = await self.db.get(Organization, org_id) if org_id else None
        if org is None:
            raise NotFound("organization in webhook not found")
        sub = await self.subscription(org)
        period_end = now + timedelta(days=PERIOD_DAYS)

        if type_ == "checkout.completed":
            session = await self.db.get(CheckoutSession, data.get("session_id", ""))
            plan = data.get("plan") or (session.plan if session else None)
            if plan not in PLANS:
                raise ServiceError("unknown plan in webhook", code="invalid_plan")
            if session is not None:
                session.status = "completed"
                session.completed_at = now
            sub.plan = plan
            sub.status = "active"
            sub.provider_customer_id = data.get("customer_id")
            sub.provider_subscription_id = data.get("subscription_id")
            sub.current_period_start = now
            sub.current_period_end = period_end
            sub.cancel_at_period_end = False
            sub.canceled_at = None
            org.plan = plan
            action = "billing.plan_changed"
        elif type_ == "invoice.paid":
            sub.status = "active"
            sub.current_period_start = now
            sub.current_period_end = period_end
            action = "billing.invoice_paid"
        elif type_ == "invoice.payment_failed":
            sub.status = "past_due"
            action = "billing.payment_failed"
        elif type_ == "subscription.canceled":
            sub.status = "canceled"
            sub.plan = "free"
            sub.cancel_at_period_end = False
            sub.canceled_at = now
            sub.current_period_end = None
            org.plan = "free"
            action = "billing.canceled"
        else:
            raise ServiceError(f"unhandled event type {type_}", code="unhandled_event")

        await self.audit.record(
            action=action,
            org_id=org.id,
            actor=None,
            actor_email="billing-webhook",
            target_type="subscription",
            target_id=sub.id,
            metadata={"plan": sub.plan, "status": sub.status, "event": type_},
        )
