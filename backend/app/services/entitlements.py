"""Plan limits and feature gates, enforced in one place."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.plans import get_plan, has_feature
from app.models import ApiKey, Membership, Organization, Project
from app.services.errors import PlanLimit


class Entitlements:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def usage(self, org: Organization) -> dict[str, dict[str, int]]:
        plan = get_plan(org.plan)
        counts = {
            "projects": await self._count(Project, Project.org_id == org.id),
            "members": await self._count(Membership, Membership.org_id == org.id),
            "api_keys": await self._count(
                ApiKey, ApiKey.org_id == org.id, ApiKey.revoked_at.is_(None)
            ),
        }
        return {k: {"used": v, "limit": plan.limits.get(k, 0)} for k, v in counts.items()}

    async def require_capacity(self, org: Organization, resource: str) -> None:
        usage = (await self.usage(org))[resource]
        if usage["limit"] != -1 and usage["used"] >= usage["limit"]:
            raise PlanLimit(
                f"the {get_plan(org.plan).name} plan allows {usage['limit']} "
                f"{resource.replace('_', ' ')}; upgrade to add more",
            )

    def require_feature(self, org: Organization, feature: str) -> None:
        if not has_feature(org.plan, feature):
            raise PlanLimit(
                f"{feature.replace('_', ' ')} is not included in the "
                f"{get_plan(org.plan).name} plan",
                code="feature_not_in_plan",
            )

    async def _count(self, model, *conditions) -> int:  # type: ignore[no-untyped-def]
        query = select(func.count()).select_from(model).where(*conditions)
        return int((await self.db.execute(query)).scalar_one())
