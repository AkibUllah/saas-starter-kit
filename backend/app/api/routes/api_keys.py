from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, client_ip, get_ctx, get_db, require_role
from app.core.context import AppContext
from app.models import Role
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/orgs/{org_id}/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
async def list_keys(
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> list:
    return await ApiKeyService(db, ctx).list(octx.org)


@router.post("", response_model=ApiKeyCreated, status_code=201)
async def create_key(
    body: ApiKeyCreate,
    request: Request,
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> ApiKeyCreated:
    assert octx.user is not None
    key, full = await ApiKeyService(db, ctx).create(
        octx.org,
        octx.user,
        name=body.name,
        scopes=body.scopes,
        expires_in_days=body.expires_in_days,
        ip=client_ip(request),
    )
    return ApiKeyCreated(**ApiKeyOut.model_validate(key).model_dump(), key=full)


@router.delete("/{key_id}", response_model=ApiKeyOut)
async def revoke_key(
    key_id: str,
    request: Request,
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    assert octx.user is not None
    return await ApiKeyService(db, ctx).revoke(octx.org, octx.user, key_id, ip=client_ip(request))
