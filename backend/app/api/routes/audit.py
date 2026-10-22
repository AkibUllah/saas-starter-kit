from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_ctx, get_db, require_role
from app.core.context import AppContext
from app.models import Role
from app.schemas.audit import AuditOut
from app.schemas.common import Page
from app.services.audit_service import AuditService
from app.services.entitlements import Entitlements

router = APIRouter(prefix="/orgs/{org_id}/audit", tags=["audit"])


@router.get("", response_model=Page[AuditOut])
async def list_audit(
    octx: OrgContext = Depends(require_role(Role.ADMIN)),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None, max_length=64),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Page[AuditOut]:
    Entitlements(db).require_feature(octx.org, "audit_log")
    items, total = await AuditService(db, ctx).list(
        octx.org.id, page=page, page_size=page_size, action=action
    )
    return Page[AuditOut](
        items=[AuditOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )
