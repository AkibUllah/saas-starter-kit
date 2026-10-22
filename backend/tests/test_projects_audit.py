from __future__ import annotations

from tests.conftest import API, set_plan


async def test_project_crud(client, owner):
    org = owner["org"]["id"]
    r = await client.post(
        f"{API}/orgs/{org}/projects", json={"name": "Checkout API", "description": "bKash + cards"}
    )
    assert r.status_code == 201
    project = r.json()
    assert (
        project["slug"] == "checkout-api"
        and project["status"] == "active"
        and project["created_by"] == owner["user"]["id"]
    )
    dup = (await client.post(f"{API}/orgs/{org}/projects", json={"name": "Checkout API"})).json()
    assert dup["slug"].startswith("checkout-api-")
    r = await client.patch(
        f"{API}/orgs/{org}/projects/{project['id']}",
        json={"status": "archived", "name": "  Checkout v2 "},
    )
    assert (
        r.status_code == 200
        and r.json()["status"] == "archived"
        and r.json()["name"] == "Checkout v2"
    )
    assert (
        await client.patch(f"{API}/orgs/{org}/projects/{project['id']}", json={"status": "bogus"})
    ).status_code == 422
    assert len((await client.get(f"{API}/orgs/{org}/projects")).json()) == 2
    assert (await client.delete(f"{API}/orgs/{org}/projects/{project['id']}")).status_code == 200
    assert (await client.get(f"{API}/orgs/{org}/projects/{project['id']}")).status_code == 404


async def test_project_limit_follows_plan(app, client, owner):
    org = owner["org"]["id"]
    for i in range(3):
        assert (
            await client.post(f"{API}/orgs/{org}/projects", json={"name": f"P{i}"})
        ).status_code == 201
    r = await client.post(f"{API}/orgs/{org}/projects", json={"name": "P4"})
    assert r.status_code == 402 and r.json()["code"] == "plan_limit_reached"
    usage = (await client.get(f"{API}/orgs/{org}/billing")).json()["usage"]
    assert usage["projects"] == {"used": 3, "limit": 3}
    await set_plan(app, org, "business")
    assert (await client.post(f"{API}/orgs/{org}/projects", json={"name": "P4"})).status_code == 201
    usage = (await client.get(f"{API}/orgs/{org}/billing")).json()["usage"]
    assert usage["projects"] == {"used": 4, "limit": -1}


async def test_audit_log_is_gated_and_records_actions(app, client, owner):
    org = owner["org"]["id"]
    await client.post(f"{API}/orgs/{org}/projects", json={"name": "Audited"})
    r = await client.get(f"{API}/orgs/{org}/audit")
    assert r.status_code == 402 and r.json()["code"] == "feature_not_in_plan"
    await set_plan(app, org, "pro")
    r = await client.get(f"{API}/orgs/{org}/audit")
    assert r.status_code == 200
    body = r.json()
    actions = [e["action"] for e in body["items"]]
    assert actions[0] == "project.created" and "org.created" in actions
    entry = body["items"][0]
    assert entry["actor_email"] == "owner@example.com" and entry["metadata"] == {"name": "Audited"}
    r = await client.get(f"{API}/orgs/{org}/audit", params={"action": "project", "page_size": 1})
    assert r.json()["total"] == 1 and r.json()["page_size"] == 1
