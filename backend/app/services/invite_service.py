from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AppContext
from app.core.mail import Message
from app.core.security import hash_token, new_opaque_token
from app.models import Invitation, Membership, Organization, Role, User
from app.services.audit_service import AuditService
from app.services.entitlements import Entitlements
from app.services.errors import Conflict, Forbidden, NotFound


class InviteService:
    def __init__(self, db: AsyncSession, ctx: AppContext) -> None:
        self.db = db
        self.ctx = ctx
        self.audit = AuditService(db, ctx)
        self.entitlements = Entitlements(db)

    async def create(
        self,
        org: Organization,
        actor: User,
        actor_role: Role,
        *,
        email: str,
        role: Role,
        ip: str = "",
    ) -> tuple[Invitation, str]:
        email = email.lower()
        if role == Role.OWNER and actor_role != Role.OWNER:
            raise Forbidden("only owners can invite owners")
        existing_member = await self.db.execute(
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .where(Membership.org_id == org.id, User.email == email)
        )
        if existing_member.scalar_one_or_none() is not None:
            raise Conflict("this person is already a member", code="already_member")
        await self.entitlements.require_capacity(org, "members")
        now = self.ctx.clock.now()
        pending = await self.db.execute(
            select(Invitation).where(
                Invitation.org_id == org.id,
                Invitation.email == email,
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
            )
        )
        for old in pending.scalars():
            old.revoked_at = now
        raw = new_opaque_token()
        invite = Invitation(
            org_id=org.id,
            email=email,
            role=role,
            token_hash=hash_token(raw),
            invited_by=actor.id,
            expires_at=now + timedelta(days=self.ctx.settings.invite_token_days),
        )
        self.db.add(invite)
        await self.db.flush()
        url = f"{self.ctx.settings.frontend_url}/accept-invite?token={raw}"
        await self.ctx.mailer.send(
            Message(
                to=email,
                subject=f"{actor.full_name} invited you to {org.name}",
                body=f"Join {org.name} as {role.value}:\n{url}\n",
                action_url=url,
                meta={"purpose": "invite", "org_id": org.id},
            )
        )
        await self.audit.record(
            action="invite.created",
            org_id=org.id,
            actor=actor,
            target_type="invite",
            target_id=invite.id,
            metadata={"email": email, "role": role.value},
            ip=ip,
        )
        return invite, raw

    async def list(self, org: Organization) -> list[Invitation]:
        res = await self.db.execute(
            select(Invitation)
            .where(Invitation.org_id == org.id)
            .order_by(Invitation.created_at.desc())
        )
        return list(res.scalars())

    async def revoke(
        self, org: Organization, actor: User, invite_id: str, *, ip: str = ""
    ) -> Invitation:
        invite = await self.db.get(Invitation, invite_id)
        if invite is None or invite.org_id != org.id:
            raise NotFound("invitation not found")
        if invite.status != "pending":
            raise Conflict(f"invitation is already {invite.status}")
        invite.revoked_at = self.ctx.clock.now()
        await self.audit.record(
            action="invite.revoked",
            org_id=org.id,
            actor=actor,
            target_type="invite",
            target_id=invite.id,
            ip=ip,
        )
        return invite

    async def _lookup(self, raw: str) -> tuple[Invitation, Organization]:
        res = await self.db.execute(
            select(Invitation).where(Invitation.token_hash == hash_token(raw))
        )
        invite = res.scalar_one_or_none()
        if invite is None:
            raise NotFound("invitation not found", code="invalid_token")
        org = await self.db.get(Organization, invite.org_id)
        if org is None:
            raise NotFound("organization no longer exists")
        return invite, org

    async def preview(self, raw: str) -> tuple[Invitation, Organization, str]:
        invite, org = await self._lookup(raw)
        status = invite.status
        if status == "pending" and invite.expires_at <= self.ctx.clock.now():
            status = "expired"
        return invite, org, status

    async def accept(
        self, raw: str, user: User, *, ip: str = ""
    ) -> tuple[Membership, Organization]:
        invite, org = await self._lookup(raw)
        now = self.ctx.clock.now()
        if invite.status != "pending":
            raise Conflict(f"invitation is {invite.status}", code=f"invite_{invite.status}")
        if invite.expires_at <= now:
            raise Conflict("invitation has expired", code="invite_expired")
        if invite.email != user.email.lower():
            raise Forbidden(
                "this invitation was sent to a different email address", code="email_mismatch"
            )
        existing = await self.db.execute(
            select(Membership).where(Membership.org_id == org.id, Membership.user_id == user.id)
        )
        membership = existing.scalar_one_or_none()
        if membership is None:
            await self.entitlements.require_capacity(org, "members")
            membership = Membership(org_id=org.id, user_id=user.id, role=invite.role)
            self.db.add(membership)
        invite.accepted_at = now
        await self.db.flush()
        await self.audit.record(
            action="invite.accepted",
            org_id=org.id,
            actor=user,
            target_type="invite",
            target_id=invite.id,
            metadata={"role": invite.role.value},
            ip=ip,
        )
        return membership, org
