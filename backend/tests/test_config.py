from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "given",
    [
        "postgres://saas:secret@db.render.internal:5432/saas",
        "postgresql://saas:secret@db.render.internal:5432/saas",
    ],
)
def test_managed_postgres_urls_are_rewritten_to_asyncpg(given: str) -> None:
    settings = Settings(_env_file=None, database_url=given)
    assert settings.database_url == "postgresql+asyncpg://saas:secret@db.render.internal:5432/saas"


@pytest.mark.parametrize(
    "given",
    [
        "sqlite+aiosqlite:///./saas.db",
        "sqlite+aiosqlite://",
        "postgresql+asyncpg://saas:saas@db:5432/saas",
    ],
)
def test_explicit_driver_urls_are_left_alone(given: str) -> None:
    assert Settings(_env_file=None, database_url=given).database_url == given
