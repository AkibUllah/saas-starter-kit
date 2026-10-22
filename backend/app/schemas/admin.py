from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserOut


class DailyCount(BaseModel):
    date: str
    count: int


class AdminStats(BaseModel):
    users_total: int
    users_verified: int
    users_active_30d: int
    orgs_total: int
    projects_total: int
    subscriptions_by_plan: dict[str, int]
    subscriptions_by_status: dict[str, int]
    mrr_cents: int
    signups_last_30_days: list[DailyCount]


class AdminUserOut(UserOut):
    org_count: int = 0


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_superuser: bool | None = None


class AdminOrgOut(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    subscription_status: str
    member_count: int
    project_count: int
    created_at: datetime
