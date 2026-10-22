from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin
from app.db.types import UtcDateTime


class RefreshToken(IdMixin, Base):
    """One row per issued refresh token. Rotation revokes the old row and links the new one
    through ``family_id`` so a replayed token can invalidate the whole chain."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    replaced_by: Mapped[str | None] = mapped_column(String(32))


class EmailToken(IdMixin, Base):
    """Single-use tokens for email verification and password reset."""

    __tablename__ = "email_tokens"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)  # verify | reset
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
