from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AppContext
from app.core.plans import get_plan
from app.models import Membership, Organization, Project, Subscription, User
from app.services.errors import NotFound


class AdminService:
    def __init__(self, db: AsyncSession, ctx: AppContext) -> None:
        self.db = db
        self.ctx = ctx

    async def _scalar(self, query) -> int:  # type: ignore[no-untyped-def]
        return int((await self.db.execute(query)).scalar_one() or 0)

    async def stats(self) -> dict:
        now = self.ctx.clock.now()
        since = now - timedelta(days=30)
        users_total = await self._scalar(select(func.count()).select_from(User))
        users_verified = await self._scalar(
            select(func.count()).select_from(User).where(User.email_verified_at.is_not(None))
        )
        users_active = await self._scalar(
            select(func.count()).select_from(User).where(User.last_login_at >= since)
        )
        orgs_total = await self._scalar(select(func.count()).select_from(Organization))
        projects_total = await self._scalar(select(func.count()).select_from(Project))

        by_plan_rows = await self.db.execute(
            select(Subscription.plan, func.count()).group_by(Subscription.plan)
        )
        by_plan = {plan: int(count) for plan, count in by_plan_rows.all()}
        by_status_rows = await self.db.execute(
            select(Subscription.status, func.count()).group_by(Subscription.status)
        )
        by_status = {status: int(count) for status, count in by_status_rows.all()}
        paying = await self.db.execute(
            select(Subscription.plan).where(Subscription.status.in_(["active", "past_due"]))
        )
        mrr = sum(get_plan(plan).price_cents for (plan,) in paying.all())

        signups_rows = await self.db.execute(
            select(User.created_at).where(User.created_at >= since)
        )
        buckets: dict[str, int] = {}
        for i in range(30):
            buckets[(since + timedelta(days=i + 1)).date().isoformat()] = 0
        for (created,) in signups_rows.all():
            key = created.date().isoformat()
            if key in buckets:
                buckets[key] += 1
        return {
            "users_total": users_total,
            "users_verified": users_verified,
            "users_active_30d": users_active,
            "orgs_total": orgs_total,
            "projects_total": projects_total,
            "subscriptions_by_plan": by_plan,
            "subscriptions_by_status": by_status,
            "mrr_cents": mrr,
            "signups_last_30_days": [{"date": d, "count": c} for d, c in buckets.items()],
        }

    async def list_users(
        self, *, q: str | None, page: int, page_size: int
    ) -> tuple[list[dict], int]:
        query = select(User)
        if q:
            like = f"%{q.lower()}%"
            query = query.where(
                func.lower(User.email).like(like) | func.lower(User.full_name).like(like)
            )
        total = await self._scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.db.execute(
            query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        users = list(rows.scalars())
        counts = await self.db.execute(
            select(Membership.user_id, func.count())
            .where(Membership.user_id.in_([u.id for u in users] or [""]))
            .group_by(Membership.user_id)
        )
        count_map = {uid: int(c) for uid, c in counts.all()}
        return [
            {
                **{
                    k: getattr(u, k)
                    for k in (
                        "id",
                        "email",
                        "full_name",
                        "is_active",
                        "is_superuser",
                        "created_at",
                        "last_login_at",
                    )
                },
                "email_verified": u.email_verified,
                "org_count": count_map.get(u.id, 0),
            }
            for u in users
        ], total

    async def update_user(
        self, actor: User, user_id: str, *, is_active: bool | None, is_superuser: bool | None
    ) -> User:
        user = await self.db.get(User, user_id)
        if user is None:
            raise NotFound("user not found")
        if is_active is not None:
            user.is_active = is_active
        if is_superuser is not None and user.id != actor.id:
            user.is_superuser = is_superuser
        return user

    async def list_orgs(
        self, *, q: str | None, page: int, page_size: int
    ) -> tuple[list[dict], int]:
        query = select(Organization)
        if q:
            like = f"%{q.lower()}%"
            query = query.where(
                func.lower(Organization.name).like(like) | Organization.slug.like(like)
            )
        total = await self._scalar(select(func.count()).select_from(query.subquery()))
        rows = await self.db.execute(
            query.order_by(Organization.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        orgs = list(rows.scalars())
        ids = [o.id for o in orgs] or [""]
        members = dict(
            (
                await self.db.execute(
                    select(Membership.org_id, func.count())
                    .where(Membership.org_id.in_(ids))
                    .group_by(Membership.org_id)
                )
            ).all()
        )
        projects = dict(
            (
                await self.db.execute(
                    select(Project.org_id, func.count())
                    .where(Project.org_id.in_(ids))
                    .group_by(Project.org_id)
                )
            ).all()
        )
        subs = dict(
            (
                await self.db.execute(
                    select(Subscription.org_id, Subscription.status).where(
                        Subscription.org_id.in_(ids)
                    )
                )
            ).all()
        )
        return [
            {
                "id": o.id,
                "name": o.name,
                "slug": o.slug,
                "plan": o.plan,
                "subscription_status": subs.get(o.id, "active"),
                "member_count": int(members.get(o.id, 0)),
                "project_count": int(projects.get(o.id, 0)),
                "created_at": o.created_at,
            }
            for o in orgs
        ], total
