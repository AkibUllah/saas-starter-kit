"""FastAPI dependencies: database session, principals (user or API key), org context, roles."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AppContext
from app.models import ApiKey, Organization, Role, User
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.errors import Forbidden, Unauthorized
from app.services.org_service import OrgService

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


@dataclass
class Principal:
    """Who is calling: a logged-in user (cookie/JWT) or an org-scoped API key."""

    user: User | None = None
    api_key: ApiKey | None = None

    @property
    def is_user(self) -> bool:
        return self.user is not None

    @property
    def scopes(self) -> set[str]:
        return set(self.api_key.scopes) if self.api_key else set()


async def get_principal(
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
    authorization: str | None = Header(default=None),
) -> Principal:
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if token and token.startswith("sk_"):
        key = await ApiKeyService(db, ctx).authenticate(token)
        return Principal(api_key=key)
    token = token or request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise Unauthorized("authentication required", code="not_authenticated")
    user = await AuthService(db, ctx).user_from_access_token(token)
    return Principal(user=user)


async def current_user(principal: Principal = Depends(get_principal)) -> User:
    if principal.user is None:
        raise Forbidden("this endpoint requires a user session, not an API key")
    return principal.user


async def superuser(user: User = Depends(current_user)) -> User:
    if not user.is_superuser:
        raise Forbidden("superuser only")
    return user


@dataclass
class OrgContext:
    org: Organization
    principal: Principal
    role: Role | None  # None for API keys

    @property
    def user(self) -> User | None:
        return self.principal.user

    def require_role(self, minimum: Role) -> None:
        if self.role is None or not self.role.at_least(minimum):
            raise Forbidden(f"requires {minimum.value} role")

    def require_scope(self, scope: str) -> None:
        if self.principal.api_key is not None and scope not in self.principal.scopes:
            raise Forbidden(f"API key lacks scope {scope}", code="missing_scope")


async def get_org_context(
    org_id: str,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> OrgContext:
    orgs = OrgService(db, ctx)
    org = await orgs.get(org_id)
    if principal.api_key is not None:
        if principal.api_key.org_id != org.id:
            raise Forbidden("API key belongs to a different organization")
        return OrgContext(org=org, principal=principal, role=None)
    assert principal.user is not None
    membership = await orgs.membership(org.id, principal.user.id)
    if membership is None:
        if principal.user.is_superuser:
            return OrgContext(org=org, principal=principal, role=Role.OWNER)
        raise Forbidden("you are not a member of this organization", code="not_a_member")
    return OrgContext(org=org, principal=principal, role=membership.role)


def require_role(minimum: Role) -> Callable[..., OrgContext]:
    async def dependency(octx: OrgContext = Depends(get_org_context)) -> OrgContext:
        octx.require_role(minimum)
        return octx

    return dependency


def require_scope(scope: str, minimum_role: Role = Role.MEMBER) -> Callable[..., OrgContext]:
    """Users need ``minimum_role``; API keys need ``scope``."""

    async def dependency(octx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if octx.principal.api_key is not None:
            octx.require_scope(scope)
        else:
            octx.require_role(minimum_role)
        return octx

    return dependency


def rate_limit(name: str, *, limit_attr: str, window_attr: str) -> Callable[..., None]:
    """Per-IP fixed-window limit for unauthenticated endpoints (login, signup, reset)."""

    async def dependency(request: Request, ctx: AppContext = Depends(get_ctx)) -> None:
        limit = getattr(ctx.settings, limit_attr)
        window = getattr(ctx.settings, window_attr)
        result = await ctx.limiter.hit(f"{name}:{client_ip(request)}", limit, window)
        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail="too many attempts, slow down",
                headers={"Retry-After": str(result.retry_after)},
            )

    return dependency


auth_rate_limit = rate_limit(
    "auth", limit_attr="login_rate_limit", window_attr="login_rate_window_seconds"
)
