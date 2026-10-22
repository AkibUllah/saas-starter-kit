from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.org import Role
from app.schemas.common import ORMModel


class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(
        default=None, min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )


class OrgUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class OrgOut(ORMModel):
    id: str
    name: str
    slug: str
    plan: str
    role: Role
    created_at: datetime


class MemberOut(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: Role
    joined_at: datetime


class MemberUpdate(BaseModel):
    role: Role


class InviteCreate(BaseModel):
    email: EmailStr
    role: Role = Role.MEMBER


class InviteOut(ORMModel):
    id: str
    email: str
    role: Role
    status: str
    expires_at: datetime
    created_at: datetime


class InvitePreview(BaseModel):
    org_name: str
    email: str
    role: Role
    expires_at: datetime
    status: str


class AcceptInviteRequest(BaseModel):
    token: str
