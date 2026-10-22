from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin
from app.db.types import UtcDateTime


class AuditEntry(IdMixin, Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_org_created", "org_id", "created_at"),)

    org_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(String(32), index=True)
    actor_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "project.created"
    target_type: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, index=True)
