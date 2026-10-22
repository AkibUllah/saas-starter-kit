from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_ctx, get_db, superuser
from app.core.context import AppContext
from app.models import User
from app.schemas.admin import AdminOrgOut, AdminStats, AdminUserOut, AdminUserUpdate
from app.schemas.common import Page
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(superuser)])


@router.get("/stats", response_model=AdminStats)
async def stats(db: AsyncSession = Depends(get_db), ctx: AppContext = Depends(get_ctx)) -> dict:
    return await AdminService(db, ctx).stats()


@router.get("/users", response_model=Page[AdminUserOut])
async def users(
    q: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Page[AdminUserOut]:
    items, total = await AdminService(db, ctx).list_users(q=q, page=page, page_size=page_size)
    return Page[AdminUserOut](
        items=[AdminUserOut(**i) for i in items], total=total, page=page, page_size=page_size
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    actor: User = Depends(superuser),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> AdminUserOut:
    user = await AdminService(db, ctx).update_user(
        actor, user_id, is_active=body.is_active, is_superuser=body.is_superuser
    )
    return AdminUserOut.model_validate(user)


@router.get("/orgs", response_model=Page[AdminOrgOut])
async def orgs(
    q: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Page[AdminOrgOut]:
    items, total = await AdminService(db, ctx).list_orgs(q=q, page=page, page_size=page_size)
    return Page[AdminOrgOut](
        items=[AdminOrgOut(**i) for i in items], total=total, page=page, page_size=page_size
    )
