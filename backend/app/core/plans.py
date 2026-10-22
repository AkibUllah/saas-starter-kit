"""Plan catalogue and entitlements.

Limits are enforced server-side in the services (``entitlements.require``); the
same table is served to the frontend so the pricing page and usage meters stay
in sync with what the API will actually allow. ``-1`` means unlimited.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_cents: int  # per month, USD
    description: str
    limits: dict[str, int]
    features: dict[str, bool]
    highlights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        price_cents=0,
        description="For trying things out and tiny side projects.",
        limits={"projects": 3, "members": 3, "api_keys": 1},
        features={"audit_log": False, "priority_support": False, "sso": False},
        highlights=["3 projects", "3 team members", "1 API key", "Community support"],
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        price_cents=2900,
        description="For small teams shipping to customers.",
        limits={"projects": 25, "members": 10, "api_keys": 10},
        features={"audit_log": True, "priority_support": True, "sso": False},
        highlights=[
            "25 projects",
            "10 team members",
            "10 API keys",
            "Audit log",
            "Priority support",
        ],
    ),
    "business": Plan(
        id="business",
        name="Business",
        price_cents=9900,
        description="For companies that need scale and compliance.",
        limits={"projects": -1, "members": 100, "api_keys": 100},
        features={"audit_log": True, "priority_support": True, "sso": True},
        highlights=["Unlimited projects", "100 team members", "100 API keys", "Audit log", "SSO"],
    ),
}

PLAN_ORDER = ["free", "pro", "business"]


def get_plan(plan_id: str) -> Plan:
    return PLANS.get(plan_id, PLANS["free"])


def is_upgrade(current: str, target: str) -> bool:
    return PLAN_ORDER.index(target) > PLAN_ORDER.index(current)


def limit_reached(plan_id: str, resource: str, current_count: int) -> bool:
    limit = get_plan(plan_id).limits.get(resource, 0)
    return limit != -1 and current_count >= limit


def has_feature(plan_id: str, feature: str) -> bool:
    return get_plan(plan_id).features.get(feature, False)
