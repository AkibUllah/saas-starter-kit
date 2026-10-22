from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Project(IdMixin, TimestampMixin, Base):
    """The demo tenant-scoped resource: proves isolation and plan limits end to end."""

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_project_org_slug"),)

    org_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="active", nullable=False
    )  # active|archived
    created_by: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="SET NULL")
    )
