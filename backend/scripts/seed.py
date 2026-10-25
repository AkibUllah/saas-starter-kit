"""Seed a demo organization and users.

    cd backend && .venv/bin/python -m scripts.seed

Idempotent: re-running prints the credentials and exits. Uses the application
services, so the data goes through the same validation, entitlement and audit
code as real requests (the Pro upgrade even goes through the mock webhook).
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.plans import PLANS
from app.db.base import Base
from app.db.session import create_engine, create_session_factory
from app.main import build_context
from app.models import Role, User
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from app.services.invite_service import InviteService
from app.services.org_service import OrgService
from app.services.project_service import ProjectService

DEMO_PASSWORD = "Demo1234!"
ADMIN_PASSWORD = "Admin1234!"
USERS = [
    ("demo@saaskit.dev", "Akib Jafor", DEMO_PASSWORD, False),
    ("fatema@saaskit.dev", "Fatema Rahman", DEMO_PASSWORD, False),
    ("rahim@saaskit.dev", "Rahim Uddin", DEMO_PASSWORD, False),
    ("admin@saaskit.dev", "Platform Admin", ADMIN_PASSWORD, True),
]
PROJECTS_ACME = [
    ("Checkout API", "Payment orchestration for bKash, Nagad and cards."),
    ("Merchant Portal", "Next.js dashboard for merchants in Dhaka and Chattogram."),
    ("Settlement Engine", "Daily settlement batches and reconciliation."),
    ("Mobile App", "Flutter customer app, phase 2."),
    ("Data Warehouse", "Nightly loads into the analytics schema."),
]
PROJECTS_BOGURA = [
    ("Field Sensors", "AWD water-level sensors across 40 paddies."),
    ("Farmer SMS", "Bangla SMS alerts for irrigation schedules."),
]


def banner(lines: list[str]) -> None:
    width = max(len(line) for line in lines) + 4
    print("+" + "-" * width + "+")
    for line in lines:
        print("| " + line.ljust(width - 2) + " |")
    print("+" + "-" * width + "+")


async def main() -> None:
    settings = get_settings()
    ctx = build_context(settings)
    engine = create_engine(settings.database_url)
    if settings.is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    factory = create_session_factory(engine)

    async with factory() as db:
        if (
            await db.execute(select(User).where(User.email == "demo@saaskit.dev"))
        ).scalar_one_or_none():
            banner(
                [
                    "Demo data already present.",
                    f"demo@saaskit.dev / {DEMO_PASSWORD}",
                    f"admin@saaskit.dev / {ADMIN_PASSWORD}",
                ]
            )
            await engine.dispose()
            return

        auth = AuthService(db, ctx)
        users: dict[str, User] = {}
        for email, name, password, superuser in USERS:
            user, _ = await auth.signup(
                email=email, password=password, full_name=name, ip="127.0.0.1", user_agent="seed"
            )
            user.email_verified_at = ctx.clock.now()
            user.is_superuser = superuser
            users[email] = user
        demo = users["demo@saaskit.dev"]

        orgs = OrgService(db, ctx)
        acme = await orgs.create(demo, "Acme Dhaka", "acme-dhaka")
        bogura = await orgs.create(demo, "Bogura Agro Supplies", "bogura-agro")

        # Pro upgrade through the mock checkout + webhook path
        billing = BillingService(db, ctx)
        session = await billing.create_checkout(acme, demo, "pro")
        await billing.complete_checkout(acme, session.id)
        acme = await orgs.get(acme.id)

        invites = InviteService(db, ctx)
        for email, role in (("fatema@saaskit.dev", Role.ADMIN), ("rahim@saaskit.dev", Role.MEMBER)):
            _, token = await invites.create(acme, demo, Role.OWNER, email=email, role=role)
            await invites.accept(token, users[email])
        await invites.create(acme, demo, Role.OWNER, email="tanvir@saaskit.dev", role=Role.MEMBER)

        projects = ProjectService(db, ctx)
        for name, description in PROJECTS_ACME:
            await projects.create(acme, demo, name=name, description=description)
        for name, description in PROJECTS_BOGURA:
            await projects.create(bogura, demo, name=name, description=description)

        _, api_key = await ApiKeyService(db, ctx).create(
            acme,
            demo,
            name="CI deploy key",
            scopes=["projects:read", "projects:write"],
            expires_in_days=365,
        )
        await db.commit()

    await engine.dispose()
    banner(
        [
            "Demo data created",
            "",
            "Owner       demo@saaskit.dev",
            f"            (Acme Dhaka: {PLANS['pro'].name}, Bogura Agro: Free)",
            "Org admin   fatema@saaskit.dev",
            "Member      rahim@saaskit.dev",
            "Superuser   admin@saaskit.dev",
            "Passwords: see 'Demo accounts' in the README",
            "",
            f"Acme Dhaka API key (shown once): {api_key}",
            "Pending invite for tanvir@saaskit.dev (link printed in the mail log above)",
        ]
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
