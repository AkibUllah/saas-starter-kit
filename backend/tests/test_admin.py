from __future__ import annotations

from tests.conftest import API, PASSWORD, create_org, login, make_superuser, new_client, signup


async def test_admin_endpoints_require_superuser(client, owner):
    assert (await client.get(f"{API}/admin/stats")).status_code == 403
    assert (await client.get(f"{API}/admin/users")).status_code == 403


async def test_admin_stats_users_and_orgs(app, client, owner):
    org = owner["org"]["id"]
    session = (await client.post(f"{API}/orgs/{org}/billing/checkout", json={"plan": "pro"})).json()
    await client.post(f"{API}/orgs/{org}/billing/checkout/{session['session_id']}/complete")
    await client.post(f"{API}/orgs/{org}/projects", json={"name": "P"})
    async with new_client(app) as other:
        await signup(other, "someone@example.com", "Some One")
        await create_org(other, "Second Org")

    await make_superuser(app, "owner@example.com")
    await login(
        client, "owner@example.com"
    )  # fresh token carries the flag; permission is checked in DB anyway

    stats = (await client.get(f"{API}/admin/stats")).json()
    assert stats["users_total"] == 2 and stats["orgs_total"] == 2 and stats["projects_total"] == 1
    assert stats["subscriptions_by_plan"] == {"pro": 1, "free": 1}
    assert stats["mrr_cents"] == 2900
    assert (
        len(stats["signups_last_30_days"]) == 30
        and sum(d["count"] for d in stats["signups_last_30_days"]) == 2
    )

    users = (await client.get(f"{API}/admin/users", params={"q": "some"})).json()
    assert (
        users["total"] == 1
        and users["items"][0]["email"] == "someone@example.com"
        and users["items"][0]["org_count"] == 1
    )

    orgs = (await client.get(f"{API}/admin/orgs")).json()
    by_slug = {o["slug"]: o for o in orgs["items"]}
    assert by_slug["acme-dhaka"]["plan"] == "pro" and by_slug["acme-dhaka"]["project_count"] == 1
    assert by_slug["second-org"]["member_count"] == 1

    # superuser can read any org even without membership
    second_id = by_slug["second-org"]["id"]
    assert (await client.get(f"{API}/orgs/{second_id}/projects")).status_code == 200

    # deactivate a user: they cannot log in or use existing tokens
    target = users["items"][0]["id"]
    r = await client.patch(f"{API}/admin/users/{target}", json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    async with new_client(app) as other:
        r = await other.post(
            f"{API}/auth/login", json={"email": "someone@example.com", "password": PASSWORD}
        )
        assert r.status_code == 401 and r.json()["code"] == "account_disabled"
    # cannot strip own superuser flag
    me = owner["user"]["id"]
    r = await client.patch(f"{API}/admin/users/{me}", json={"is_superuser": False})
    assert r.json()["is_superuser"] is True
    assert (
        await client.patch(f"{API}/admin/users/nope", json={"is_active": True})
    ).status_code == 404
