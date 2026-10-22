from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

ALLOWED_SCOPES = ("org:read", "projects:read", "projects:write")


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scopes: list[str] = Field(default_factory=lambda: ["projects:read"])
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)

    @field_validator("scopes")
    @classmethod
    def _known_scopes(cls, scopes: list[str]) -> list[str]:
        unknown = sorted(set(scopes) - set(ALLOWED_SCOPES))
        if unknown:
            raise ValueError(f"unknown scopes: {', '.join(unknown)}")
        if not scopes:
            raise ValueError("at least one scope is required")
        return sorted(set(scopes))


class ApiKeyOut(ORMModel):
    id: str
    name: str
    prefix: str
    masked: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeyCreated(ApiKeyOut):
    key: str
