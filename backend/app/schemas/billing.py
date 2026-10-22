from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PlanOut(BaseModel):
    id: str
    name: str
    price_cents: int
    description: str
    limits: dict[str, int]
    features: dict[str, bool]
    highlights: list[str]


class SubscriptionOut(ORMModel):
    plan: str
    status: str
    provider: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    trial_ends_at: datetime | None = None
    cancel_at_period_end: bool
    canceled_at: datetime | None = None
    seats: int


class Usage(BaseModel):
    used: int
    limit: int  # -1 = unlimited


class BillingOverview(BaseModel):
    subscription: SubscriptionOut
    plan: PlanOut
    usage: dict[str, Usage]
    features: dict[str, bool]
    plans: list[PlanOut]


class CheckoutCreate(BaseModel):
    plan: str = Field(pattern=r"^(pro|business)$")


class CheckoutOut(BaseModel):
    session_id: str
    url: str
    plan: str
    amount_cents: int
    status: str


class WebhookEvent(BaseModel):
    id: str
    type: str
    created: int
    data: dict[str, Any]


class BillingEventOut(ORMModel):
    id: str
    event_id: str
    type: str
    received_at: datetime
    processed: bool
    error: str | None = None
