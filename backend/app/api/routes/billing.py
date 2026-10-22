from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, client_ip, get_ctx, get_db, require_role
from app.core.context import AppContext
from app.core.plans import PLAN_ORDER, PLANS
from app.models import Role
from app.schemas.billing import (
    BillingEventOut,
    BillingOverview,
    CheckoutCreate,
    CheckoutOut,
    PlanOut,
    SubscriptionOut,
)
from app.services.billing_service import BillingService

router = APIRouter(tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
async def plans() -> list[dict]:
    return [PLANS[p].to_dict() for p in PLAN_ORDER]


@router.get("/orgs/{org_id}/billing", response_model=BillingOverview)
async def overview(
    octx: OrgContext = Depends(require_role(Role.MEMBER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    return await BillingService(db, ctx).overview(octx.org)


@router.post("/orgs/{org_id}/billing/checkout", response_model=CheckoutOut, status_code=201)
async def create_checkout(
    body: CheckoutCreate,
    request: Request,
    octx: OrgContext = Depends(require_role(Role.OWNER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> CheckoutOut:
    assert octx.user is not None
    svc = BillingService(db, ctx)
    session = await svc.create_checkout(octx.org, octx.user, body.plan, ip=client_ip(request))
    return CheckoutOut(
        session_id=session.id,
        url=svc.checkout_url(session),
        plan=session.plan,
        amount_cents=PLANS[session.plan].price_cents,
        status=session.status,
    )


@router.get("/orgs/{org_id}/billing/checkout/{session_id}", response_model=CheckoutOut)
async def get_checkout(
    session_id: str,
    octx: OrgContext = Depends(require_role(Role.OWNER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> CheckoutOut:
    svc = BillingService(db, ctx)
    session = await svc.get_checkout(octx.org, session_id)
    return CheckoutOut(
        session_id=session.id,
        url=svc.checkout_url(session),
        plan=session.plan,
        amount_cents=PLANS[session.plan].price_cents,
        status=session.status,
    )


@router.post(
    "/orgs/{org_id}/billing/checkout/{session_id}/complete", response_model=SubscriptionOut
)
async def complete_checkout(
    session_id: str,
    octx: OrgContext = Depends(require_role(Role.OWNER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    """Mock provider only: stands in for the customer paying on the hosted checkout page."""
    return await BillingService(db, ctx).complete_checkout(octx.org, session_id)


@router.post("/orgs/{org_id}/billing/cancel", response_model=SubscriptionOut)
async def cancel(
    request: Request,
    octx: OrgContext = Depends(require_role(Role.OWNER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    assert octx.user is not None
    return await BillingService(db, ctx).cancel(octx.org, octx.user, ip=client_ip(request))


@router.post("/orgs/{org_id}/billing/resume", response_model=SubscriptionOut)
async def resume(
    request: Request,
    octx: OrgContext = Depends(require_role(Role.OWNER)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    assert octx.user is not None
    return await BillingService(db, ctx).resume(octx.org, octx.user, ip=client_ip(request))


@router.post("/billing/webhooks/mock", response_model=BillingEventOut)
async def webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
    x_mock_timestamp: str = Header(default=""),
    x_mock_signature: str = Header(default=""),
):  # type: ignore[no-untyped-def]
    """Provider -> us. Verified with HMAC-SHA256 over ``<timestamp>.<body>``."""
    body = await request.body()
    return await BillingService(db, ctx).handle_webhook(body, x_mock_timestamp, x_mock_signature)
