from __future__ import annotations

from tests.conftest import API, create_org, new_client, signup


async def test_create_org_makes_owner_with_free_plan(client, owner):
    org = owner["org"]
    assert org["role"] == "owner" and org["plan"] == "free" and org["slug"] == "acme-dhaka"
    r = await client.get(f"{API}/orgs")
    assert [o["id"] for o in r.json()] == [org["id"]]
    members = (await client.get(f"{API}/orgs/{org['id']}/members")).json()
    assert len(members) == 1 and members[0]["role"] == "owner"
    billing = (await client.get(f"{API}/orgs/{org['id']}/billing")).json()
    assert (
        billing["subscription"]["plan"] == "free" and billing["subscription"]["status"] == "active"
    )


async def test_slug_collision_is_resolved_or_rejected(client, owner):
    second = await create_org(client, "Acme Dhaka")
    assert second["slug"].startswith("acme-dhaka-") and second["slug"] != owner["org"]["slug"]
    r = await client.post(f"{API}/orgs", json={"name": "Other", "slug": "acme-dhaka"})
    assert r.status_code == 409 and r.json()["code"] == "slug_taken"
    r = await client.post(f"{API}/orgs", json={"name": "Other", "slug": "Bad Slug!"})
    assert r.status_code == 422


async def test_tenant_isolation(app, client, owner):
    org_a = owner["org"]["id"]
    project = (await client.post(f"{API}/orgs/{org_a}/projects", json={"name": "Secret"})).json()
    async with new_client(app) as other:
        await signup(other, "intruder@example.com")
        org_b = (await create_org(other, "Intruder Inc"))["id"]
        assert (await other.get(f"{API}/orgs/{org_a}")).status_code == 403
        assert (await other.get(f"{API}/orgs/{org_a}/projects")).status_code == 403
        # a valid project id from org A does not resolve under org B
        assert (await other.get(f"{API}/orgs/{org_b}/projects/{project['id']}")).status_code == 404
        assert (await other.get(f"{API}/orgs/{org_b}/projects")).json() == []
    assert (await client.get(f"{API}/orgs/doesnotexist")).status_code == 404


async def _add_member(app, client, owner_org: str, email: str, role: str):
    """Invite + accept helper; returns the member's own client (still open) and user id."""
    r = await client.post(f"{API}/orgs/{owner_org}/invites", json={"email": email, "role": role})
    assert r.status_code == 201, r.text
    token = app.state.ctx.mailer.last_for(email).action_url.split("token=")[1]
    member_client = new_client(app)
    data = await signup(member_client, email, email.split("@")[0])
    r = await member_client.post(f"{API}/invites/accept", json={"token": token})
    assert r.status_code == 200, r.text
    return member_client, data["user"]["id"]


async def test_role_management_rules(app, client, owner):
    org = owner["org"]["id"]
    admin_client, admin_id = await _add_member(app, client, org, "admin@example.com", "admin")
    member_client, member_id = await _add_member(app, client, org, "member@example.com", "member")
    try:
        # admin cannot grant owner
        r = await admin_client.patch(
            f"{API}/orgs/{org}/members/{member_id}", json={"role": "owner"}
        )
        assert r.status_code == 403
        # admin can promote member to admin
        r = await admin_client.patch(
            f"{API}/orgs/{org}/members/{member_id}", json={"role": "admin"}
        )
        assert r.status_code == 200 and r.json()["role"] == "admin"
        # member (now admin) demoting the owner: only owners may touch owners
        r = await member_client.patch(
            f"{API}/orgs/{org}/members/{owner['user']['id']}", json={"role": "member"}
        )
        assert r.status_code == 403
        # the single owner cannot demote themselves
        r = await client.patch(
            f"{API}/orgs/{org}/members/{owner['user']['id']}", json={"role": "admin"}
        )
        assert r.status_code == 409 and r.json()["code"] == "last_owner"
        # owner promotes admin to owner, then can step down
        r = await client.patch(f"{API}/orgs/{org}/members/{admin_id}", json={"role": "owner"})
        assert r.status_code == 200
        r = await client.patch(
            f"{API}/orgs/{org}/members/{owner['user']['id']}", json={"role": "member"}
        )
        assert r.status_code == 200 and r.json()["role"] == "member"
        # a plain member cannot update org settings; an owner can
        r = await client.patch(f"{API}/orgs/{org}", json={"name": "Renamed"})
        assert r.status_code == 403
        r = await admin_client.patch(f"{API}/orgs/{org}", json={"name": "Renamed"})
        assert r.status_code == 200 and r.json()["name"] == "Renamed"
    finally:
        await admin_client.aclose()
        await member_client.aclose()


async def test_remove_and_leave(app, client, owner):
    org = owner["org"]["id"]
    member_client, member_id = await _add_member(app, client, org, "leaver@example.com", "member")
    try:
        # member cannot remove the owner
        r = await member_client.delete(f"{API}/orgs/{org}/members/{owner['user']['id']}")
        assert r.status_code == 403
        # last owner cannot leave
        r = await client.delete(f"{API}/orgs/{org}/members/{owner['user']['id']}")
        assert r.status_code == 409 and r.json()["code"] == "last_owner"
        # member can leave
        r = await member_client.delete(f"{API}/orgs/{org}/members/{member_id}")
        assert r.status_code == 200
        assert (await member_client.get(f"{API}/orgs/{org}")).status_code == 403
        assert len((await client.get(f"{API}/orgs/{org}/members")).json()) == 1
    finally:
        await member_client.aclose()


async def test_delete_org_requires_owner(app, client, owner):
    org = owner["org"]["id"]
    admin_client, _ = await _add_member(app, client, org, "adm@example.com", "admin")
    try:
        assert (await admin_client.delete(f"{API}/orgs/{org}")).status_code == 403
        assert (await client.delete(f"{API}/orgs/{org}")).status_code == 200
        assert (await client.get(f"{API}/orgs")).json() == []
    finally:
        await admin_client.aclose()
