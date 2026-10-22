from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, client_ip, get_ctx, get_db, require_scope
from app.core.context import AppContext
from app.models import Role
from app.schemas.common import Message
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/orgs/{org_id}/projects", tags=["projects"])

read = require_scope("projects:read", Role.MEMBER)
write = require_scope("projects:write", Role.MEMBER)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    octx: OrgContext = Depends(read),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> list:
    return await ProjectService(db, ctx).list(octx.org)


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    request: Request,
    octx: OrgContext = Depends(write),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    return await ProjectService(db, ctx).create(
        octx.org, octx.user, name=body.name, description=body.description, ip=client_ip(request)
    )


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    octx: OrgContext = Depends(read),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    return await ProjectService(db, ctx).get(octx.org, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    request: Request,
    octx: OrgContext = Depends(write),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
):  # type: ignore[no-untyped-def]
    return await ProjectService(db, ctx).update(
        octx.org, octx.user, project_id, body.model_dump(exclude_unset=True), ip=client_ip(request)
    )


@router.delete("/{project_id}", response_model=Message)
async def delete_project(
    project_id: str,
    request: Request,
    octx: OrgContext = Depends(write),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    await ProjectService(db, ctx).delete(octx.org, octx.user, project_id, ip=client_ip(request))
    return Message(detail="project deleted")
