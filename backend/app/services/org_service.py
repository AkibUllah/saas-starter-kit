from __future__ import annotations

import re
import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import AppContext
from app.models import Membership, Organization, Role, Subscription, User
from app.services.audit_service import AuditService
from app.services.errors import Conflict, Forbidden, NotFound


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "org"


class OrgService:
    def __init__(self, db: AsyncSession, ctx: AppContext) -> None:
        self.db = db
        self.ctx = ctx
        self.audit = AuditService(db, ctx)

    async def create(
        self, owner: User, name: str, slug: str | None = None, *, ip: str = ""
    ) -> Organization:
        base = slug or slugify(name)
        candidate = base
        while await self.get_by_slug(candidate) is not None:
            if slug:
                raise Conflict("slug is already taken", code="slug_taken")
            candidate = f"{base}-{secrets.token_hex(2)}"
        now = self.ctx.clock.now()
        org = Organization(name=name.strip(), slug=candidate, plan="free", created_by=owner.id)
        self.db.add(org)
        await self.db.flush()
        self.db.add(Membership(org_id=org.id, user_id=owner.id, role=Role.OWNER))
        self.db.add(
            Subscription(
                org_id=org.id,
                plan="free",
                status="active",
                provider="mock",
                current_period_start=now,
                seats=1,
            )
        )
        await self.db.flush()
        await self.audit.record(
            action="org.created",
            org_id=org.id,
            actor=owner,
            target_type="org",
            target_id=org.id,
            ip=ip,
        )
        return org

    async def get(self, org_id: str) -> Organization:
        org = await self.db.get(Organization, org_id)
        if org is None:
            raise NotFound("organization not found")
        return org

    async def get_by_slug(self, slug: str) -> Organization | None:
        res = await self.db.execute(select(Organization).where(Organization.slug == slug))
        return res.scalar_one_or_none()

    async def list_for_user(self, user: User) -> list[tuple[Organization, Role]]:
        res = await self.db.execute(
            select(Membership)
            .options(selectinload(Membership.organization))
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at)
        )
        return [(m.organization, m.role) for m in res.scalars()]

    async def membership(self, org_id: str, user_id: str) -> Membership | None:
        res = await self.db.execute(
            select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
        )
        return res.scalar_one_or_none()

    async def update(
        self, org: Organization, actor: User, *, name: str, ip: str = ""
    ) -> Organization:
        org.name = name.strip()
        await self.audit.record(
            action="org.updated", org_id=org.id, actor=actor, metadata={"name": name}, ip=ip
        )
        return org

    async def delete(self, org: Organization, actor: User, *, ip: str = "") -> None:
        await self.audit.record(
            action="org.deleted",
            org_id=None,
            actor=actor,
            target_type="org",
            target_id=org.id,
            ip=ip,
        )
        await self.db.delete(org)
        await self.db.flush()

    # ------------------------------------------------------------ members
    async def members(self, org: Organization) -> list[tuple[Membership, User]]:
        res = await self.db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.org_id == org.id)
            .order_by(Membership.created_at)
        )
        return [(m, u) for m, u in res.all()]

    async def member_count(self, org_id: str) -> int:
        res = await self.db.execute(
            select(func.count()).select_from(Membership).where(Membership.org_id == org_id)
        )
        return int(res.scalar_one())

    async def owner_count(self, org_id: str) -> int:
        res = await self.db.execute(
            select(func.count())
            .select_from(Membership)
            .where(Membership.org_id == org_id, Membership.role == Role.OWNER)
        )
        return int(res.scalar_one())

    async def change_role(
        self,
        org: Organization,
        actor: User,
        actor_role: Role,
        target_user_id: str,
        role: Role,
        *,
        ip: str = "",
    ) -> Membership:
        target = await self.membership(org.id, target_user_id)
        if target is None:
            raise NotFound("member not found")
        if (target.role == Role.OWNER or role == Role.OWNER) and actor_role != Role.OWNER:
            raise Forbidden("only owners can grant or revoke the owner role")
        if target.role == Role.OWNER and role != Role.OWNER and await self.owner_count(org.id) == 1:
            raise Conflict("an organization needs at least one owner", code="last_owner")
        previous = target.role
        target.role = role
        await self.audit.record(
            action="member.role_changed",
            org_id=org.id,
            actor=actor,
            target_type="user",
            target_id=target_user_id,
            metadata={"from": previous.value, "to": role.value},
            ip=ip,
        )
        return target

    async def remove_member(
        self, org: Organization, actor: User, actor_role: Role, target_user_id: str, *, ip: str = ""
    ) -> None:
        target = await self.membership(org.id, target_user_id)
        if target is None:
            raise NotFound("member not found")
        is_self = target_user_id == actor.id
        if not is_self and not actor_role.at_least(Role.ADMIN):
            raise Forbidden("admins or owners can remove members")
        if not is_self and target.role == Role.OWNER and actor_role != Role.OWNER:
            raise Forbidden("only owners can remove another owner")
        if target.role == Role.OWNER and await self.owner_count(org.id) == 1:
            raise Conflict("transfer ownership before leaving", code="last_owner")
        await self.db.delete(target)
        await self.audit.record(
            action="member.left" if is_self else "member.removed",
            org_id=org.id,
            actor=actor,
            target_type="user",
            target_id=target_user_id,
            ip=ip,
        )
        await self.db.flush()
