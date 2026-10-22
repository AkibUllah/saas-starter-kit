"""Signup, login, token rotation, email verification and password reset."""

from __future__ import annotations

import logging
from datetime import timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AppContext
from app.core.mail import Message
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)
from app.db.base import new_id
from app.models import EmailToken, RefreshToken, User
from app.schemas.auth import TokenPair
from app.services.audit_service import AuditService
from app.services.errors import Conflict, Locked, NotFound, Unauthorized

log = logging.getLogger("app.auth")

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


class AuthService:
    def __init__(self, db: AsyncSession, ctx: AppContext) -> None:
        self.db = db
        self.ctx = ctx
        self.settings = ctx.settings
        self.audit = AuditService(db, ctx)

    # ------------------------------------------------------------ lookups
    async def get_user_by_email(self, email: str) -> User | None:
        res = await self.db.execute(select(User).where(User.email == email.lower()))
        return res.scalar_one_or_none()

    async def get_user(self, user_id: str) -> User | None:
        return await self.db.get(User, user_id)

    async def user_from_access_token(self, token: str) -> User:
        try:
            payload = decode_access_token(self.settings, token, self.ctx.clock.now())
        except jwt.ExpiredSignatureError:
            raise Unauthorized("access token expired", code="token_expired") from None
        except jwt.InvalidTokenError:
            raise Unauthorized("invalid access token") from None
        user = await self.get_user(payload["sub"])
        if user is None or not user.is_active:
            raise Unauthorized("account disabled or missing")
        return user

    # ------------------------------------------------------------ signup / login
    async def signup(self, *, email: str, password: str, full_name: str, ip: str, user_agent: str):
        email = email.lower()
        if await self.get_user_by_email(email):
            raise Conflict("an account with this email already exists", code="email_taken")
        user = User(email=email, full_name=full_name.strip(), password_hash=hash_password(password))
        self.db.add(user)
        await self.db.flush()
        await self.send_verification(user)
        await self.audit.record(action="user.signup", org_id=None, actor=user, ip=ip)
        tokens = await self.issue_tokens(user, ip=ip, user_agent=user_agent)
        return user, tokens

    async def login(self, *, email: str, password: str, ip: str, user_agent: str):
        now = self.ctx.clock.now()
        user = await self.get_user_by_email(email)
        if user is None:
            raise Unauthorized("invalid email or password", code="invalid_credentials")
        if user.locked_until and user.locked_until > now:
            seconds = int((user.locked_until - now).total_seconds())
            raise Locked(f"account locked, try again in {seconds}s", code="account_locked")
        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_LOGINS:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_attempts = 0
                await self.audit.record(action="user.locked", org_id=None, actor=user, ip=ip)
            await self.db.commit()  # the raised error would otherwise roll this back
            raise Unauthorized("invalid email or password", code="invalid_credentials")
        if not user.is_active:
            raise Unauthorized("account disabled", code="account_disabled")
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        tokens = await self.issue_tokens(user, ip=ip, user_agent=user_agent)
        await self.audit.record(action="user.login", org_id=None, actor=user, ip=ip)
        return user, tokens

    # ------------------------------------------------------------ tokens
    async def issue_tokens(
        self, user: User, *, ip: str, user_agent: str, family_id: str | None = None
    ) -> TokenPair:
        now = self.ctx.clock.now()
        raw_refresh = new_opaque_token()
        row = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=family_id or new_id(),
            user_agent=user_agent[:255],
            ip=ip[:64],
            created_at=now,
            expires_at=now + timedelta(days=self.settings.refresh_token_days),
        )
        self.db.add(row)
        await self.db.flush()
        access = create_access_token(
            self.settings, subject=user.id, now=now, extra={"su": user.is_superuser}
        )
        return TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=self.settings.access_token_minutes * 60,
        )

    async def refresh(self, raw_refresh: str, *, ip: str, user_agent: str):
        now = self.ctx.clock.now()
        res = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh))
        )
        row = res.scalar_one_or_none()
        if row is None:
            raise Unauthorized("invalid refresh token", code="invalid_refresh")
        if row.revoked_at is not None:
            # Replay of an already rotated token: somebody else holds a copy. Kill the family.
            await self.db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            log.warning(
                "refresh token reuse detected user=%s family=%s", row.user_id, row.family_id
            )
            await self.audit.record(
                action="user.refresh_reuse_detected",
                org_id=None,
                actor=None,
                target_type="user",
                target_id=row.user_id,
                ip=ip,
            )
            raise Unauthorized("refresh token reuse detected", code="refresh_reused")
        if row.expires_at <= now:
            raise Unauthorized("refresh token expired", code="refresh_expired")
        user = await self.get_user(row.user_id)
        if user is None or not user.is_active:
            raise Unauthorized("account disabled or missing")
        tokens = await self.issue_tokens(
            user, ip=ip, user_agent=user_agent, family_id=row.family_id
        )
        new_row = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(tokens.refresh_token))
        )
        row.revoked_at = now
        row.replaced_by = new_row.scalar_one().id
        await self.db.flush()
        return user, tokens

    async def logout(self, raw_refresh: str | None) -> None:
        if not raw_refresh:
            return
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == hash_token(raw_refresh),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=self.ctx.clock.now())
        )

    async def revoke_all_sessions(self, user: User) -> int:
        res = await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=self.ctx.clock.now())
        )
        return res.rowcount or 0

    # ------------------------------------------------------------ email tokens
    async def _issue_email_token(self, user: User, purpose: str, hours: int) -> str:
        now = self.ctx.clock.now()
        raw = new_opaque_token()
        await self.db.execute(
            update(EmailToken)
            .where(
                EmailToken.user_id == user.id,
                EmailToken.purpose == purpose,
                EmailToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        self.db.add(
            EmailToken(
                user_id=user.id,
                purpose=purpose,
                token_hash=hash_token(raw),
                created_at=now,
                expires_at=now + timedelta(hours=hours),
            )
        )
        await self.db.flush()
        return raw

    async def _consume_email_token(self, raw: str, purpose: str) -> User:
        now = self.ctx.clock.now()
        res = await self.db.execute(
            select(EmailToken).where(
                EmailToken.token_hash == hash_token(raw), EmailToken.purpose == purpose
            )
        )
        token = res.scalar_one_or_none()
        if token is None or token.used_at is not None or token.expires_at <= now:
            raise NotFound("this link is invalid or has expired", code="invalid_token")
        token.used_at = now
        user = await self.get_user(token.user_id)
        if user is None:
            raise NotFound("this link is invalid or has expired", code="invalid_token")
        return user

    async def send_verification(self, user: User) -> None:
        if user.email_verified:
            return
        raw = await self._issue_email_token(user, "verify", self.settings.email_token_hours)
        url = f"{self.settings.frontend_url}/verify-email?token={raw}"
        await self.ctx.mailer.send(
            Message(
                to=user.email,
                subject=f"Verify your email for {self.settings.app_name}",
                body=f"Hi {user.full_name},\n\nConfirm your email address by opening:\n{url}\n",
                action_url=url,
                meta={"purpose": "verify"},
            )
        )

    async def verify_email(self, raw: str) -> User:
        user = await self._consume_email_token(raw, "verify")
        if not user.email_verified:
            user.email_verified_at = self.ctx.clock.now()
            await self.audit.record(action="user.email_verified", org_id=None, actor=user)
        return user

    async def forgot_password(self, email: str) -> None:
        user = await self.get_user_by_email(email)
        if user is None or not user.is_active:
            return  # same response either way; do not leak account existence
        raw = await self._issue_email_token(user, "reset", 2)
        url = f"{self.settings.frontend_url}/reset-password?token={raw}"
        await self.ctx.mailer.send(
            Message(
                to=user.email,
                subject=f"Reset your {self.settings.app_name} password",
                body=f"Hi {user.full_name},\n\nReset your password within 2 hours:\n{url}\n",
                action_url=url,
                meta={"purpose": "reset"},
            )
        )

    async def reset_password(self, raw: str, new_password: str) -> User:
        user = await self._consume_email_token(raw, "reset")
        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.revoke_all_sessions(user)
        await self.audit.record(action="user.password_reset", org_id=None, actor=user)
        return user

    async def change_password(self, user: User, current: str, new_password: str) -> None:
        if not verify_password(current, user.password_hash):
            raise Unauthorized("current password is incorrect", code="invalid_credentials")
        user.password_hash = hash_password(new_password)
        await self.revoke_all_sessions(user)
        await self.audit.record(action="user.password_changed", org_id=None, actor=user)
