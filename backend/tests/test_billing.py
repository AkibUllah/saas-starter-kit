from __future__ import annotations

import json

from app.core.clock import ManualClock
from app.services.billing_service import MockBillingProvider
from tests.conftest import API, login, new_client, signup


def signed(secret: str, clock: ManualClock, type_: str, data: dict, event_id: str | None = None):
    provider = MockBillingProvider(secret, clock)
    event = provider.event(type_, data)
    if event_id:
        event["id"] = event_id
    s = provider.sign(event)
    return s.body, {"X-Mock-Timestamp": s.timestamp, "X-Mock-Signature": s.signature}


async def test_plans_are_public(client):
    r = await client.get(f"{API}/plans")
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == ["free", "pro", "business"]
    assert r.json()[1]["price_cents"] == 2900 and r.json()[2]["limits"]["projects"] == -1


async def test_checkout_completes_through_webhook(client, owner):
    org = owner["org"]["id"]
    r = await client.post(f"{API}/orgs/{org}/billing/checkout", json={"plan": "pro"})
    assert r.status_code == 201
    session = r.json()
    assert (
        session["url"]
        == f"http://front.test/dashboard/billing/checkout?session={session['session_id']}"
    )
    assert session["amount_cents"] == 2900 and session["status"] == "open"
    assert (
        await client.post(f"{API}/orgs/{org}/billing/checkout", json={"plan": "free"})
    ).status_code == 422

    r = await client.post(f"{API}/orgs/{org}/billing/checkout/{session['session_id']}/complete")
    assert r.status_code == 200
    sub = r.json()
    assert (
        sub["plan"] == "pro" and sub["status"] == "active" and sub["current_period_end"] is not None
    )
    r = await client.get(f"{API}/orgs/{org}/billing/checkout/{session['session_id']}")
    assert r.json()["status"] == "completed"
    assert (
        await client.post(f"{API}/orgs/{org}/billing/checkout/{session['session_id']}/complete")
    ).status_code == 409

    overview = (await client.get(f"{API}/orgs/{org}/billing")).json()
    assert overview["plan"]["id"] == "pro" and overview["usage"]["projects"]["limit"] == 25
    assert overview["features"]["audit_log"] is True
    assert (await client.get(f"{API}/orgs/{org}")).json()["plan"] == "pro"
    r = await client.post(f"{API}/orgs/{org}/billing/checkout", json={"plan": "pro"})
    assert r.status_code == 409 and r.json()["code"] == "same_plan"
    audit = (await client.get(f"{API}/orgs/{org}/audit", params={"action": "billing"})).json()
    assert {e["action"] for e in audit["items"]} == {
        "billing.checkout_started",
        "billing.plan_changed",
    }


async def test_webhook_signature_timestamp_and_idempotency(app, client, owner, clock: ManualClock):
    org = owner["org"]["id"]
    secret = app.state.ctx.settings.billing_webhook_secret
    body, headers = signed(
        secret, clock, "checkout.completed", {"org_id": org, "plan": "business"}, event_id="evt_1"
    )

    bad = dict(headers, **{"X-Mock-Signature": "0" * 64})
    r = await client.post(f"{API}/billing/webhooks/mock", content=body, headers=bad)
    assert r.status_code == 401 and r.json()["code"] == "bad_signature"
    r = await client.post(f"{API}/billing/webhooks/mock", content=body, headers={})
    assert r.status_code == 401

    r = await client.post(f"{API}/billing/webhooks/mock", content=body, headers=headers)
    assert (
        r.status_code == 200 and r.json()["processed"] is True and r.json()["event_id"] == "evt_1"
    )
    assert (await client.get(f"{API}/orgs/{org}")).json()["plan"] == "business"

    # replay: same event id, no second processing even if the body differs
    body2, headers2 = signed(
        secret, clock, "subscription.canceled", {"org_id": org}, event_id="evt_1"
    )
    r = await client.post(f"{API}/billing/webhooks/mock", content=body2, headers=headers2)
    assert r.status_code == 200 and r.json()["type"] == "checkout.completed"
    assert (await client.get(f"{API}/orgs/{org}")).json()["plan"] == "business"

    # stale signature
    clock.advance(minutes=10)
    r = await client.post(f"{API}/billing/webhooks/mock", content=body2, headers=headers2)
    assert r.status_code == 401 and r.json()["code"] == "stale_webhook"

    # unknown org is recorded but not applied
    body3, headers3 = signed(secret, clock, "invoice.paid", {"org_id": "nope"})
    r = await client.post(f"{API}/billing/webhooks/mock", content=body3, headers=headers3)
    assert (
        r.status_code == 200 and r.json()["processed"] is False and "not found" in r.json()["error"]
    )

    # malformed
    raw = b'{"nope": true}'
    provider = MockBillingProvider(secret, clock)
    ts = str(int(clock.now().timestamp()))
    from app.core.security import sign_payload

    r = await client.post(
        f"{API}/billing/webhooks/mock",
        content=raw,
        headers={"X-Mock-Timestamp": ts, "X-Mock-Signature": sign_payload(secret, raw, ts)},
    )
    assert r.status_code == 400 and r.json()["code"] == "bad_payload"
    assert provider.name == "mock"
    assert json.loads(body)["type"] == "checkout.completed"


async def test_payment_failed_paid_and_canceled_events(app, client, owner, clock: ManualClock):
    org = owner["org"]["id"]
    secret = app.state.ctx.settings.billing_webhook_secret
    session = (await client.post(f"{API}/orgs/{org}/billing/checkout", json={"plan": "pro"})).json()
    await client.post(f"{API}/orgs/{org}/billing/checkout/{session['session_id']}/complete")

    body, headers = signed(secret, clock, "invoice.payment_failed", {"org_id": org})
    await client.post(f"{API}/billing/webhooks/mock", content=body, headers=headers)
    sub = (await client.get(f"{API}/orgs/{org}/billing")).json()["subscription"]
    assert sub["status"] == "past_due" and sub["plan"] == "pro"

    clock.advance(days=1)
    await login(client, "owner@example.com")
    body, headers = signed(secret, clock, "invoice.paid", {"org_id": org})
    await client.post(f"{API}/billing/webhooks/mock", content=body, headers=headers)
    sub = (await client.get(f"{API}/orgs/{org}/billing")).json()["subscription"]
    assert sub["status"] == "active"

    body, headers = signed(secret, clock, "subscription.canceled", {"org_id": org})
    await client.post(f"{API}/billing/webhooks/mock", content=body, headers=headers)
    overview = (await client.get(f"{API}/orgs/{org}/billing")).json()
    assert overview["subscription"]["status"] == "canceled" and overview["plan"]["id"] == "free"
    assert (await client.get(f"{API}/orgs/{org}")).json()["plan"] == "free"


async def test_cancel_and_resume_at_period_end(client, owner):
    org = owner["org"]["id"]
    r = await client.post(f"{API}/orgs/{org}/billing/cancel")
    assert r.status_code == 409 and r.json()["code"] == "free_plan"
    session = (
        await client.post(f"{API}/orgs/{org}/billing/checkout", json={"plan": "business"})
    ).json()
    await client.post(f"{API}/orgs/{org}/billing/checkout/{session['session_id']}/complete")
    r = await client.post(f"{API}/orgs/{org}/billing/cancel")
    assert (
        r.status_code == 200
        and r.json()["cancel_at_period_end"] is True
        and r.json()["status"] == "active"
    )
    r = await client.post(f"{API}/orgs/{org}/billing/resume")
    assert r.status_code == 200 and r.json()["cancel_at_period_end"] is False
    assert (await client.post(f"{API}/orgs/{org}/billing/resume")).status_code == 409


async def test_billing_actions_require_owner(app, client, owner):
    org = owner["org"]["id"]
    await client.post(
        f"{API}/orgs/{org}/invites", json={"email": "adm@example.com", "role": "admin"}
    )
    token = app.state.ctx.mailer.last_for("adm@example.com").action_url.split("token=")[1]
    async with new_client(app) as admin:
        await signup(admin, "adm@example.com")
        await admin.post(f"{API}/invites/accept", json={"token": token})
        assert (await admin.get(f"{API}/orgs/{org}/billing")).status_code == 200
        assert (
            await admin.post(f"{API}/orgs/{org}/billing/checkout", json={"plan": "pro"})
        ).status_code == 403
        assert (await admin.post(f"{API}/orgs/{org}/billing/cancel")).status_code == 403
