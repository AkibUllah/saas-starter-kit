from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMModel


class UserOut(ORMModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    email_verified: bool
    created_at: datetime
    last_login_at: datetime | None = None


class UserUpdate(ORMModel):
    full_name: str = Field(min_length=1, max_length=120)
