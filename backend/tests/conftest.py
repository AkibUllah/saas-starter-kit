from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.clock import ManualClock, use_clock
from app.core.config import Settings
from app.core.context import AppContext
from app.core.mail import ConsoleMailer
from app.core.rate_limit import MemoryRateLimiter
from app.db.base import Base
from app.db.session import create_engine, create_session_factory
from app.main import create_app

API = "/api/v1"
PASSWORD = "Str0ngPass!"


def make_settings(**overrides) -> Settings:  # type: ignore[no-untyped-def]
    base = {
        "env": "test",
        "secret_key": "unit-test-secret-key-0123456789-abcdef",
        "database_url": "sqlite+aiosqlite:///:memory:",
        "redis_url": None,
        "log_json": False,
        "cookie_secure": False,
        "login_rate_limit": 1000,
        "frontend_url": "http://front.test",
        "_env_file": None,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def clock() -> ManualClock:
    manual = ManualClock()
    previous = use_clock(manual)  # model defaults (created_at/updated_at) follow the test clock
    yield manual
    use_clock(previous)


@pytest.fixture
def mailer() -> ConsoleMailer:
    return ConsoleMailer()


@pytest.fixture
def settings() -> Settings:
    return make_settings()


async def build_app(settings: Settings, clock: ManualClock, mailer: ConsoleMailer):  # type: ignore[no-untyped-def]
    ctx = AppContext(settings=settings, clock=clock, mailer=mailer, limiter=MemoryRateLimiter())
    application = create_app(settings, ctx=ctx)
    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    application.state.engine = engine
    application.state.session_factory = create_session_factory(engine)
    return application


@pytest.fixture
async def app(settings: Settings, clock: ManualClock, mailer: ConsoleMailer):  # type: ignore[no-untyped-def]
    application = await build_app(settings, clock, mailer)
    yield application
    await application.state.engine.dispose()


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def new_client(app) -> AsyncClient:  # type: ignore[no-untyped-def]
    """A second browser: separate cookie jar."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def signup(
    client: AsyncClient, email: str, name: str = "Test User", password: str = PASSWORD
) -> dict:
    r = await client.post(
        f"{API}/auth/signup", json={"email": email, "password": password, "full_name": name}
    )
    assert r.status_code == 201, r.text
    return r.json()


async def login(client: AsyncClient, email: str, password: str = PASSWORD) -> dict:
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


async def create_org(client: AsyncClient, name: str = "Acme Dhaka") -> dict:
    r = await client.post(f"{API}/orgs", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


def bearer(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
async def owner(client: AsyncClient) -> dict:
    """Signed-in owner (cookies on ``client``) with one org: {'user', 'org', 'tokens'}."""
    data = await signup(client, "owner@example.com", "Owner One")
    org = await create_org(client)
    return {"user": data["user"], "org": org, "tokens": data}


async def make_superuser(app, email: str) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import update

    from app.models import User

    async with app.state.session_factory() as db:
        await db.execute(update(User).where(User.email == email).values(is_superuser=True))
        await db.commit()


async def set_plan(app, org_id: str, plan: str) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import update

    from app.models import Organization, Subscription

    async with app.state.session_factory() as db:
        await db.execute(update(Organization).where(Organization.id == org_id).values(plan=plan))
        await db.execute(
            update(Subscription).where(Subscription.org_id == org_id).values(plan=plan)
        )
        await db.commit()
