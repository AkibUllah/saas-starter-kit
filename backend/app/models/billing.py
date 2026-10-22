from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.db.types import UtcDateTime


class Subscription(IdMixin, TimestampMixin, Base):
    """One subscription per organization. ``status`` follows the usual provider vocabulary."""

    __tablename__ = "subscriptions"

    org_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    # trialing | active | past_due | canceled
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    provider_customer_id: Mapped[str | None] = mapped_column(String(64))
    provider_subscription_id: Mapped[str | None] = mapped_column(String(64))
    current_period_start: Mapped[datetime | None] = mapped_column(UtcDateTime)
    current_period_end: Mapped[datetime | None] = mapped_column(UtcDateTime)
    trial_ends_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    seats: Mapped[int] = mapped_column(default=1, nullable=False)


class CheckoutSession(IdMixin, Base):
    """A pending upgrade started from the billing page and completed by the provider webhook."""

    __tablename__ = "checkout_sessions"

    org_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="open"
    )  # open|completed|expired
    created_by: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class BillingEvent(IdMixin, Base):
    """Every webhook event received, keyed by the provider event id for idempotency."""

    __tablename__ = "billing_events"

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    org_id: Mapped[str | None] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
