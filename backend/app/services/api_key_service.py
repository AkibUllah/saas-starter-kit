from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AppContext
from app.core.security import hash_token, new_api_key
from app.models import ApiKey, Organization, User
from app.services.audit_service import AuditService
from app.services.entitlements import Entitlements
from app.services.errors import NotFound, Unauthorized

LAST_USED_WRITE_INTERVAL = timedelta(seconds=60)


class ApiKeyService:
    def __init__(self, db: AsyncSession, ctx: AppContext) -> None:
        self.db = db
        self.ctx = ctx
        self.audit = AuditService(db, ctx)
        self.entitlements = Entitlements(db)

    async def create(
        self,
        org: Organization,
        actor: User,
        *,
        name: str,
        scopes: list[str],
        expires_in_days: int | None,
        ip: str = "",
    ) -> tuple[ApiKey, str]:
        await self.entitlements.require_capacity(org, "api_keys")
        full, prefix, key_hash = new_api_key()
        now = self.ctx.clock.now()
        key = ApiKey(
            org_id=org.id,
            name=name.strip(),
            prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            created_by=actor.id,
            expires_at=now + timedelta(days=expires_in_days) if expires_in_days else None,
        )
        self.db.add(key)
        await self.db.flush()
        await self.audit.record(
            action="api_key.created",
            org_id=org.id,
            actor=actor,
            target_type="api_key",
            target_id=key.id,
            metadata={"name": name, "scopes": scopes, "prefix": prefix},
            ip=ip,
        )
        return key, full

    async def list(self, org: Organization) -> list[ApiKey]:
        res = await self.db.execute(
            select(ApiKey).where(ApiKey.org_id == org.id).order_by(ApiKey.created_at.desc())
        )
        return list(res.scalars())

    async def revoke(self, org: Organization, actor: User, key_id: str, *, ip: str = "") -> ApiKey:
        key = await self.db.get(ApiKey, key_id)
        if key is None or key.org_id != org.id:
            raise NotFound("API key not found")
        if key.revoked_at is None:
            key.revoked_at = self.ctx.clock.now()
            await self.audit.record(
                action="api_key.revoked",
                org_id=org.id,
                actor=actor,
                target_type="api_key",
                target_id=key.id,
                metadata={"prefix": key.prefix},
                ip=ip,
            )
        return key

    async def authenticate(self, full_key: str) -> ApiKey:
        res = await self.db.execute(select(ApiKey).where(ApiKey.key_hash == hash_token(full_key)))
        key = res.scalar_one_or_none()
        now = self.ctx.clock.now()
        if key is None or key.revoked_at is not None:
            raise Unauthorized("invalid API key", code="invalid_api_key")
        if key.expires_at is not None and key.expires_at <= now:
            raise Unauthorized("API key expired", code="api_key_expired")
        if key.last_used_at is None or now - key.last_used_at > LAST_USED_WRITE_INTERVAL:
            key.last_used_at = now
        return key
