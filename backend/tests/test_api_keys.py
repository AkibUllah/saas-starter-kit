from __future__ import annotations

from app.core.clock import ManualClock
from tests.conftest import API, create_org, login, new_client, set_plan, signup


async def test_api_key_lifecycle_and_scopes(app, client, owner):
    org = owner["org"]["id"]
    r = await client.post(
        f"{API}/orgs/{org}/api-keys",
        json={"name": "CI", "scopes": ["projects:read"], "expires_in_days": 30},
    )
    assert r.status_code == 201
    created = r.json()
    key = created["key"]
    assert (
        key.startswith("sk_live_")
        and created["prefix"] in key
        and created["masked"].endswith("••••••••")
    )
    listed = (await client.get(f"{API}/orgs/{org}/api-keys")).json()
    assert len(listed) == 1 and "key" not in listed[0] and listed[0]["scopes"] == ["projects:read"]

    await client.post(f"{API}/orgs/{org}/projects", json={"name": "Visible"})
    async with new_client(app) as api:
        headers = {"Authorization": f"Bearer {key}"}
        r = await api.get(f"{API}/orgs/{org}/projects", headers=headers)
        assert r.status_code == 200 and r.json()[0]["name"] == "Visible"
        # read-only scope cannot write
        r = await api.post(f"{API}/orgs/{org}/projects", json={"name": "Nope"}, headers=headers)
        assert r.status_code == 403 and r.json()["code"] == "missing_scope"
        # API keys are not users
        assert (await api.get(f"{API}/users/me", headers=headers)).status_code == 403
        assert (await api.get(f"{API}/orgs/{org}/members", headers=headers)).status_code == 403
        # wrong org
        other_org = (await create_org(client, "Second"))["id"]
        assert (
            await api.get(f"{API}/orgs/{other_org}/projects", headers=headers)
        ).status_code == 403
        # last_used_at recorded
        listed = (await client.get(f"{API}/orgs/{org}/api-keys")).json()
        assert listed[0]["last_used_at"] is not None

        # revoke
        r = await client.delete(f"{API}/orgs/{org}/api-keys/{created['id']}")
        assert r.status_code == 200 and r.json()["revoked_at"] is not None
        r = await api.get(f"{API}/orgs/{org}/projects", headers=headers)
        assert r.status_code == 401 and r.json()["code"] == "invalid_api_key"
        assert (
            await api.get(
                f"{API}/orgs/{org}/projects", headers={"Authorization": "Bearer sk_live_bogus"}
            )
        ).status_code == 401


async def test_api_key_expiry_and_plan_limit(app, client, owner, clock: ManualClock):
    org = owner["org"]["id"]
    r = await client.post(
        f"{API}/orgs/{org}/api-keys",
        json={"name": "short", "scopes": ["org:read", "projects:write"], "expires_in_days": 1},
    )
    key = r.json()["key"]
    # free plan allows exactly one active key
    r = await client.post(f"{API}/orgs/{org}/api-keys", json={"name": "second"})
    assert r.status_code == 402 and r.json()["code"] == "plan_limit_reached"
    await set_plan(app, org, "business")
    assert (
        await client.post(f"{API}/orgs/{org}/api-keys", json={"name": "second"})
    ).status_code == 201

    async with new_client(app) as api:
        headers = {"Authorization": f"Bearer {key}"}
        r = await api.post(f"{API}/orgs/{org}/projects", json={"name": "From key"}, headers=headers)
        assert r.status_code == 201 and r.json()["created_by"] is None
        clock.advance(days=2)
        r = await api.get(f"{API}/orgs/{org}/projects", headers=headers)
        assert r.status_code == 401 and r.json()["code"] == "api_key_expired"
    await login(client, "owner@example.com")

    r = await client.post(
        f"{API}/orgs/{org}/api-keys", json={"name": "bad", "scopes": ["admin:everything"]}
    )
    assert r.status_code == 422


async def test_api_keys_require_admin_role(app, client, owner):
    org = owner["org"]["id"]
    await client.post(f"{API}/orgs/{org}/invites", json={"email": "member@example.com"})
    token = app.state.ctx.mailer.last_for("member@example.com").action_url.split("token=")[1]
    async with new_client(app) as member:
        await signup(member, "member@example.com")
        await member.post(f"{API}/invites/accept", json={"token": token})
        assert (await member.get(f"{API}/orgs/{org}/api-keys")).status_code == 403
        assert (
            await member.post(f"{API}/orgs/{org}/api-keys", json={"name": "x"})
        ).status_code == 403
