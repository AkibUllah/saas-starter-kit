from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AppContext
from app.models import Organization, Project, User
from app.services.audit_service import AuditService
from app.services.entitlements import Entitlements
from app.services.errors import NotFound
from app.services.org_service import slugify


class ProjectService:
    def __init__(self, db: AsyncSession, ctx: AppContext) -> None:
        self.db = db
        self.ctx = ctx
        self.audit = AuditService(db, ctx)
        self.entitlements = Entitlements(db)

    async def list(self, org: Organization) -> list[Project]:
        res = await self.db.execute(
            select(Project).where(Project.org_id == org.id).order_by(Project.created_at.desc())
        )
        return list(res.scalars())

    async def get(self, org: Organization, project_id: str) -> Project:
        project = await self.db.get(Project, project_id)
        if project is None or project.org_id != org.id:  # cross-tenant ids look like 404s
            raise NotFound("project not found")
        return project

    async def create(
        self,
        org: Organization,
        actor: User | None,
        *,
        name: str,
        description: str = "",
        ip: str = "",
    ) -> Project:
        await self.entitlements.require_capacity(org, "projects")
        base = slugify(name)
        slug = base
        while (
            await self.db.execute(
                select(Project).where(Project.org_id == org.id, Project.slug == slug)
            )
        ).scalar_one_or_none() is not None:
            slug = f"{base}-{secrets.token_hex(2)}"
        project = Project(
            org_id=org.id,
            name=name.strip(),
            slug=slug,
            description=description,
            created_by=actor.id if actor else None,
        )
        self.db.add(project)
        await self.db.flush()
        await self.audit.record(
            action="project.created",
            org_id=org.id,
            actor=actor,
            target_type="project",
            target_id=project.id,
            metadata={"name": project.name},
            ip=ip,
        )
        return project

    async def update(
        self, org: Organization, actor: User | None, project_id: str, changes: dict, *, ip: str = ""
    ) -> Project:
        project = await self.get(org, project_id)
        for field, value in changes.items():
            if value is not None:
                setattr(
                    project,
                    field,
                    value.strip() if isinstance(value, str) and field == "name" else value,
                )
        await self.audit.record(
            action="project.updated",
            org_id=org.id,
            actor=actor,
            target_type="project",
            target_id=project.id,
            metadata={k: v for k, v in changes.items() if v is not None},
            ip=ip,
        )
        return project

    async def delete(
        self, org: Organization, actor: User | None, project_id: str, *, ip: str = ""
    ) -> None:
        project = await self.get(org, project_id)
        await self.audit.record(
            action="project.deleted",
            org_id=org.id,
            actor=actor,
            target_type="project",
            target_id=project.id,
            metadata={"name": project.name},
            ip=ip,
        )
        await self.db.delete(project)
        await self.db.flush()
