from __future__ import annotations

from app.core.plans import PLAN_ORDER, get_plan, has_feature, is_upgrade, limit_reached
from app.core.rate_limit import MemoryRateLimiter
from app.core.security import (
    hash_password,
    hash_token,
    new_api_key,
    sign_payload,
    verify_password,
    verify_signature,
)
from app.models import Role
from app.services.org_service import slugify


def test_plan_helpers():
    assert PLAN_ORDER == ["free", "pro", "business"]
    assert is_upgrade("free", "pro") and not is_upgrade("business", "pro")
    assert limit_reached("free", "projects", 3) and not limit_reached("free", "projects", 2)
    assert not limit_reached("business", "projects", 10_000)
    assert has_feature("pro", "audit_log") and not has_feature("free", "audit_log")
    assert get_plan("unknown").id == "free"


def test_password_and_token_hashing():
    hashed = hash_password("Str0ngPass!")
    assert hashed.startswith("$2") and verify_password("Str0ngPass!", hashed)
    assert not verify_password("other", hashed) and not verify_password("x", "not-a-hash")
    assert hash_token("abc") == hash_token("abc") and len(hash_token("abc")) == 64


def test_api_key_format_and_signatures():
    full, prefix, digest = new_api_key()
    parts = full.split("_")
    assert parts[:2] == ["sk", "live"] and parts[2] == prefix and len(prefix) == 8
    assert digest == hash_token(full)
    body = b'{"id":"evt_1"}'
    sig = sign_payload("secret", body, "1700000000")
    assert verify_signature("secret", body, "1700000000", sig)
    assert not verify_signature("secret", body, "1700000001", sig)
    assert not verify_signature("other", body, "1700000000", sig)


def test_roles_and_slugify():
    assert Role.OWNER.at_least(Role.ADMIN) and Role.ADMIN.at_least(Role.MEMBER)
    assert not Role.MEMBER.at_least(Role.ADMIN)
    assert slugify("Acme Dhaka Ltd.") == "acme-dhaka-ltd"
    assert slugify("!!!") == "org"
    assert len(slugify("x" * 100)) == 48


async def test_memory_rate_limiter_window():
    limiter = MemoryRateLimiter()
    results = [await limiter.hit("ip:1", 2, 60) for _ in range(3)]
    assert [r.allowed for r in results] == [True, True, False]
    assert results[-1].retry_after > 0 and results[1].remaining == 0
    await limiter.reset("ip:1")
    assert (await limiter.hit("ip:1", 2, 60)).allowed
