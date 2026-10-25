"""Application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import admin, api_keys, audit, auth, billing, health, orgs, projects, users
from app.core.clock import SystemClock
from app.core.config import Settings, get_settings
from app.core.context import AppContext
from app.core.logging import RequestContextMiddleware, configure_logging
from app.core.mail import ConsoleMailer
from app.core.rate_limit import MemoryRateLimiter, RedisRateLimiter
from app.db.session import create_engine, create_session_factory
from app.services.errors import ServiceError

log = logging.getLogger("app")


def build_context(settings: Settings) -> AppContext:
    redis: Any | None = None
    limiter: Any = MemoryRateLimiter()
    if settings.redis_url:
        from redis import asyncio as aioredis

        redis = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
        limiter = RedisRateLimiter(redis)
    return AppContext(
        settings=settings, clock=SystemClock(), mailer=ConsoleMailer(), limiter=limiter, redis=redis
    )


def create_app(settings: Settings | None = None, *, ctx: AppContext | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(json_logs=settings.log_json, level=settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        if not hasattr(app.state, "engine"):
            app.state.engine = create_engine(settings.database_url)
            app.state.session_factory = create_session_factory(app.state.engine)
        if not hasattr(app.state, "ctx"):
            app.state.ctx = build_context(settings)
        log.info(
            "starting %s env=%s db=%s",
            settings.app_name,
            settings.env,
            settings.database_url.split("@")[-1],
        )
        yield
        await app.state.engine.dispose()
        if app.state.ctx.redis is not None:
            close = getattr(app.state.ctx.redis, "aclose", None) or app.state.ctx.redis.close
            await close()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.1",
        description=(
            "Multi-tenant SaaS backend: auth, organizations, team invites, "
            "API keys, plans, billing, audit."
        ),
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    if ctx is not None:
        app.state.ctx = ctx

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.exception_handler(ServiceError)
    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]),
                "message": e["msg"],
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": "validation failed", "code": "validation_error", "errors": errors},
        )

    app.include_router(health.router)
    for router in (auth, users, orgs, api_keys, projects, billing, audit, admin):
        app.include_router(router.router, prefix=settings.api_prefix)
    return app


app = create_app()
