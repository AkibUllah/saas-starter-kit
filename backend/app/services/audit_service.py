from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AppContext
from app.models import AuditEntry, User


class AuditService:
    def __init__(self, db: AsyncSession, ctx: AppContext) -> None:
        self.db = db
        self.ctx = ctx

    async def record(
        self,
        *,
        action: str,
        org_id: str | None,
        actor: User | None,
        target_type: str = "",
        target_id: str = "",
        metadata: dict[str, Any] | None = None,
        ip: str = "",
        actor_email: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            org_id=org_id,
            actor_id=actor.id if actor else None,
            actor_email=actor_email or (actor.email if actor else ""),
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_=metadata or {},
            ip=ip,
            created_at=self.ctx.clock.now(),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list(
        self, org_id: str, *, page: int = 1, page_size: int = 50, action: str | None = None
    ) -> tuple[list[AuditEntry], int]:
        query = select(AuditEntry).where(AuditEntry.org_id == org_id)
        if action:
            query = query.where(AuditEntry.action.like(f"{action}%"))
        total = (
            await self.db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()
        rows = await self.db.execute(
            query.order_by(AuditEntry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows.scalars()), total
