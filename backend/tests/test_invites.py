from __future__ import annotations

from app.core.clock import ManualClock
from app.core.mail import ConsoleMailer
from tests.conftest import API, login, new_client, set_plan, signup


async def test_invite_flow(app, client, owner, mailer: ConsoleMailer):
    org = owner["org"]["id"]
    r = await client.post(
        f"{API}/orgs/{org}/invites", json={"email": "Fatema@Example.com", "role": "admin"}
    )
    assert r.status_code == 201
    invite = r.json()
    assert invite["email"] == "fatema@example.com" and invite["status"] == "pending"
    mail = mailer.last_for("fatema@example.com")
    token = mail.action_url.split("token=")[1]

    # public preview before signing up
    r = await client.get(f"{API}/invites/preview", params={"token": token})
    assert (
        r.status_code == 200
        and r.json()["org_name"] == "Acme Dhaka"
        and r.json()["role"] == "admin"
    )

    async with new_client(app) as invitee:
        await signup(invitee, "fatema@example.com", "Fatema")
        r = await invitee.post(f"{API}/invites/accept", json={"token": token})
        assert r.status_code == 200 and r.json()["role"] == "admin"
        orgs = (await invitee.get(f"{API}/orgs")).json()
        assert [o["id"] for o in orgs] == [org]
        # accepting twice is a conflict
        r = await invitee.post(f"{API}/invites/accept", json={"token": token})
        assert r.status_code == 409 and r.json()["code"] == "invite_accepted"

    listed = (await client.get(f"{API}/orgs/{org}/invites")).json()
    assert listed[0]["status"] == "accepted"


async def test_invite_email_mismatch_revoked_and_expired(
    app, client, owner, mailer: ConsoleMailer, clock: ManualClock
):
    org = owner["org"]["id"]
    await client.post(f"{API}/orgs/{org}/invites", json={"email": "right@example.com"})
    token = mailer.last_for("right@example.com").action_url.split("token=")[1]
    async with new_client(app) as wrong:
        await signup(wrong, "wrong@example.com")
        r = await wrong.post(f"{API}/invites/accept", json={"token": token})
        assert r.status_code == 403 and r.json()["code"] == "email_mismatch"

    # re-inviting the same address revokes the earlier token
    r = await client.post(f"{API}/orgs/{org}/invites", json={"email": "right@example.com"})
    assert r.status_code == 201
    r = await client.get(f"{API}/invites/preview", params={"token": token})
    assert r.json()["status"] == "revoked"
    new_token = mailer.last_for("right@example.com").action_url.split("token=")[1]

    clock.advance(days=8)
    await login(client, "owner@example.com")  # the 15-minute access token expired with the jump
    r = await client.get(f"{API}/invites/preview", params={"token": new_token})
    assert r.json()["status"] == "expired"
    async with new_client(app) as late:
        await signup(late, "right@example.com")
        r = await late.post(f"{API}/invites/accept", json={"token": new_token})
        assert r.status_code == 409 and r.json()["code"] == "invite_expired"

    # explicit revoke
    r = await client.post(f"{API}/orgs/{org}/invites", json={"email": "third@example.com"})
    invite_id = r.json()["id"]
    r = await client.delete(f"{API}/orgs/{org}/invites/{invite_id}")
    assert r.status_code == 200 and r.json()["status"] == "revoked"
    assert (await client.delete(f"{API}/orgs/{org}/invites/{invite_id}")).status_code == 409
    assert (
        await client.get(f"{API}/invites/preview", params={"token": "bogus"})
    ).status_code == 404


async def test_member_limit_enforced_on_invite(app, client, owner):
    org = owner["org"]["id"]
    # free plan: 3 members. Owner + 2 accepted invites fills it.
    for i in range(2):
        email = f"m{i}@example.com"
        assert (
            await client.post(f"{API}/orgs/{org}/invites", json={"email": email})
        ).status_code == 201
        token = app.state.ctx.mailer.last_for(email).action_url.split("token=")[1]
        async with new_client(app) as m:
            await signup(m, email)
            assert (await m.post(f"{API}/invites/accept", json={"token": token})).status_code == 200
    r = await client.post(f"{API}/orgs/{org}/invites", json={"email": "overflow@example.com"})
    assert r.status_code == 402 and r.json()["code"] == "plan_limit_reached"
    assert "Free plan allows 3 members" in r.json()["detail"]
    await set_plan(app, org, "pro")
    assert (
        await client.post(f"{API}/orgs/{org}/invites", json={"email": "overflow@example.com"})
    ).status_code == 201
    # inviting an existing member is a conflict, and only owners can invite owners
    r = await client.post(f"{API}/orgs/{org}/invites", json={"email": "m0@example.com"})
    assert r.status_code == 409 and r.json()["code"] == "already_member"
