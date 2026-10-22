from __future__ import annotations

import pytest

from app.core.clock import ManualClock
from app.core.mail import ConsoleMailer
from tests.conftest import (
    API,
    PASSWORD,
    bearer,
    build_app,
    login,
    make_settings,
    new_client,
    signup,
)


async def test_signup_sets_cookies_and_sends_verification(client, mailer: ConsoleMailer):
    data = await signup(client, "akib@example.com", "Akib Jafor")
    assert data["user"]["email"] == "akib@example.com"
    assert data["user"]["email_verified"] is False
    assert data["token_type"] == "bearer" and data["expires_in"] == 15 * 60
    assert client.cookies.get("access_token") and client.cookies.get("refresh_token")
    mail = mailer.last_for("akib@example.com")
    assert mail is not None and mail.action_url.startswith("http://front.test/verify-email?token=")
    me = await client.get(f"{API}/users/me")
    assert me.status_code == 200 and me.json()["full_name"] == "Akib Jafor"


async def test_signup_duplicate_and_weak_password(client):
    await signup(client, "dup@example.com")
    r = await client.post(
        f"{API}/auth/signup",
        json={"email": "DUP@example.com", "password": PASSWORD, "full_name": "x"},
    )
    assert r.status_code == 409 and r.json()["code"] == "email_taken"
    r = await client.post(
        f"{API}/auth/signup",
        json={"email": "weak@example.com", "password": "short", "full_name": "x"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"
    assert any(e["field"] == "password" for e in r.json()["errors"])


async def test_login_failures_lock_the_account(client, clock: ManualClock):
    await signup(client, "lock@example.com")
    for _ in range(4):
        r = await client.post(
            f"{API}/auth/login", json={"email": "lock@example.com", "password": "wrong1234"}
        )
        assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"
    r = await client.post(
        f"{API}/auth/login", json={"email": "lock@example.com", "password": "wrong1234"}
    )
    assert r.status_code == 401
    r = await client.post(
        f"{API}/auth/login", json={"email": "lock@example.com", "password": PASSWORD}
    )
    assert r.status_code == 423 and r.json()["code"] == "account_locked"
    clock.advance(minutes=16)
    r = await client.post(
        f"{API}/auth/login", json={"email": "lock@example.com", "password": PASSWORD}
    )
    assert r.status_code == 200
    assert r.json()["user"]["last_login_at"] is not None


async def test_unknown_email_is_indistinguishable(client):
    r = await client.post(
        f"{API}/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"


async def test_bearer_token_works_without_cookies(app, client):
    data = await signup(client, "bearer@example.com")
    async with new_client(app) as other:
        r = await other.get(f"{API}/users/me", headers=bearer(data))
        assert r.status_code == 200
        r = await other.get(f"{API}/users/me")
        assert r.status_code == 401 and r.json()["code"] == "not_authenticated"


async def test_access_token_expires(client, clock: ManualClock):
    data = await signup(client, "exp@example.com")
    clock.advance(minutes=16)
    r = await client.get(f"{API}/users/me", headers=bearer(data))
    assert r.status_code == 401 and r.json()["code"] == "token_expired"


async def test_refresh_rotates_and_detects_reuse(app, client, clock: ManualClock):
    data = await signup(client, "rot@example.com")
    first_refresh = data["refresh_token"]
    clock.advance(minutes=20)
    async with new_client(app) as api:
        r = await api.post(f"{API}/auth/refresh", json={"refresh_token": first_refresh})
        assert r.status_code == 200
        second = r.json()
        assert second["refresh_token"] != first_refresh
        # access token from the new pair works
        assert (await api.get(f"{API}/users/me", headers=bearer(second))).status_code == 200
        # replaying the first token revokes the whole family, including the second token
        r = await api.post(f"{API}/auth/refresh", json={"refresh_token": first_refresh})
        assert r.status_code == 401 and r.json()["code"] == "refresh_reused"
        r = await api.post(f"{API}/auth/refresh", json={"refresh_token": second["refresh_token"]})
        assert r.status_code == 401 and r.json()["code"] == "refresh_reused"


async def test_refresh_via_cookie_and_expiry(client, clock: ManualClock):
    await signup(client, "cookie@example.com")
    clock.advance(minutes=30)
    r = await client.post(f"{API}/auth/refresh")
    assert r.status_code == 200
    assert client.cookies.get("refresh_token") == r.json()["refresh_token"]
    clock.advance(days=31)
    r = await client.post(f"{API}/auth/refresh")
    assert r.status_code == 401 and r.json()["code"] == "refresh_expired"


async def test_logout_revokes_refresh_and_clears_cookies(client):
    data = await signup(client, "out@example.com")
    r = await client.post(f"{API}/auth/logout")
    assert r.status_code == 200
    assert not client.cookies.get("access_token") and not client.cookies.get("refresh_token")
    assert (await client.get(f"{API}/users/me")).status_code == 401
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 401


async def test_verify_email_token_is_single_use(client, mailer: ConsoleMailer):
    await signup(client, "verify@example.com")
    token = mailer.last_for("verify@example.com").action_url.split("token=")[1]
    r = await client.post(f"{API}/auth/verify-email", json={"token": token})
    assert r.status_code == 200 and r.json()["email_verified"] is True
    r = await client.post(f"{API}/auth/verify-email", json={"token": token})
    assert r.status_code == 404 and r.json()["code"] == "invalid_token"
    r = await client.post(f"{API}/auth/resend-verification")
    assert r.json()["detail"] == "email already verified"


async def test_password_reset_flow_revokes_sessions(app, client, mailer: ConsoleMailer):
    data = await signup(client, "reset@example.com")
    r = await client.post(f"{API}/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 200 and mailer.last_for("ghost@example.com") is None
    r = await client.post(f"{API}/auth/forgot-password", json={"email": "reset@example.com"})
    assert r.status_code == 200
    token = mailer.last_for("reset@example.com").action_url.split("token=")[1]
    r = await client.post(
        f"{API}/auth/reset-password", json={"token": token, "password": "NewPass123"}
    )
    assert r.status_code == 200
    async with new_client(app) as api:
        r = await api.post(
            f"{API}/auth/login", json={"email": "reset@example.com", "password": PASSWORD}
        )
        assert r.status_code == 401
        await login(api, "reset@example.com", "NewPass123")
        r = await api.post(f"{API}/auth/refresh", json={"refresh_token": data["refresh_token"]})
        assert r.status_code == 401  # old session revoked by the reset


async def test_change_password_requires_current(client):
    await signup(client, "chg@example.com")
    r = await client.post(
        f"{API}/auth/change-password",
        json={"current_password": "nope12345", "new_password": "Another123"},
    )
    assert r.status_code == 401
    r = await client.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Another123"},
    )
    assert r.status_code == 200
    await login(client, "chg@example.com", "Another123")


async def test_login_rate_limit(clock: ManualClock, mailer: ConsoleMailer):
    settings = make_settings(login_rate_limit=3, login_rate_window_seconds=60)
    app = await build_app(settings, clock, mailer)
    try:
        async with new_client(app) as c:
            for _ in range(3):
                r = await c.post(
                    f"{API}/auth/login", json={"email": "x@example.com", "password": PASSWORD}
                )
                assert r.status_code == 401
            r = await c.post(
                f"{API}/auth/login", json={"email": "x@example.com", "password": PASSWORD}
            )
            assert r.status_code == 429 and "Retry-After" in r.headers
    finally:
        await app.state.engine.dispose()


@pytest.mark.parametrize("path", ["/health", "/health/ready"])
async def test_health_endpoints(client, path):
    r = await client.get(path)
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert "X-Request-ID" in r.headers
