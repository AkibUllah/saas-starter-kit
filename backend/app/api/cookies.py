from __future__ import annotations

from fastapi import Response

from app.api.deps import ACCESS_COOKIE, REFRESH_COOKIE
from app.core.config import Settings
from app.schemas.auth import TokenPair


def set_auth_cookies(response: Response, settings: Settings, tokens: TokenPair) -> None:
    common = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "domain": settings.cookie_domain,
        "path": "/",
    }
    response.set_cookie(ACCESS_COOKIE, tokens.access_token, max_age=tokens.expires_in, **common)
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.refresh_token_days * 86400,
        **common,
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/", domain=settings.cookie_domain)
