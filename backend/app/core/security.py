"""Password hashing, JWT issuing/verification and opaque token helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import Settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    settings: Settings, *, subject: str, now: datetime, extra: dict[str, Any] | None = None
) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(settings: Settings, token: str, now: datetime) -> dict[str, Any]:
    """Verify signature and shape; expiry is checked against the injected clock."""
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[ALGORITHM],
        options={"verify_exp": False, "verify_iat": False},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    if int(payload.get("exp", 0)) <= int(now.timestamp()):
        raise jwt.ExpiredSignatureError("access token expired")
    return payload


def new_opaque_token(nbytes: int = 32) -> str:
    """URL-safe random secret for refresh tokens, email links and invites."""
    return base64.urlsafe_b64encode(secrets.token_bytes(nbytes)).rstrip(b"=").decode()


def hash_token(token: str) -> str:
    """Store only a SHA-256 digest of opaque tokens so a DB leak does not leak sessions."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_api_key(prefix_env: str = "live") -> tuple[str, str, str]:
    """Return (full_key, public_prefix, secret_hash).

    Format: ``sk_live_<8 char prefix>_<32 char secret>``. The prefix is stored in
    clear so keys can be identified in the UI; only the hash of the whole key is
    kept for verification.
    """
    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(24)
    full = f"sk_{prefix_env}_{prefix}_{secret}"
    return full, prefix, hash_token(full)


def sign_payload(secret: str, body: bytes, timestamp: str) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return mac.hexdigest()


def verify_signature(secret: str, body: bytes, timestamp: str, signature: str) -> bool:
    expected = sign_payload(secret, body, timestamp)
    return hmac.compare_digest(expected, signature)
