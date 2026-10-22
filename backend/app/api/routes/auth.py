from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.cookies import clear_auth_cookies, set_auth_cookies
from app.api.deps import (
    REFRESH_COOKIE,
    auth_rate_limit,
    client_ip,
    current_user,
    get_ctx,
    get_db,
    user_agent,
)
from app.core.context import AppContext
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenPair,
    VerifyEmailRequest,
)
from app.schemas.common import Message
from app.schemas.user import UserOut
from app.services.auth_service import AuthService
from app.services.errors import Unauthorized

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthResponse(TokenPair):
    user: UserOut


def _auth_response(
    response: Response, ctx: AppContext, user: User, tokens: TokenPair
) -> AuthResponse:
    set_auth_cookies(response, ctx.settings, tokens)
    return AuthResponse(**tokens.model_dump(), user=UserOut.model_validate(user))


@router.post(
    "/signup", response_model=AuthResponse, status_code=201, dependencies=[Depends(auth_rate_limit)]
)
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> AuthResponse:
    user, tokens = await AuthService(db, ctx).signup(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        ip=client_ip(request),
        user_agent=user_agent(request),
    )
    return _auth_response(response, ctx, user, tokens)


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(auth_rate_limit)])
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> AuthResponse:
    user, tokens = await AuthService(db, ctx).login(
        email=body.email,
        password=body.password,
        ip=client_ip(request),
        user_agent=user_agent(request),
    )
    return _auth_response(response, ctx, user, tokens)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> AuthResponse:
    raw = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise Unauthorized("no refresh token", code="invalid_refresh")
    try:
        user, tokens = await AuthService(db, ctx).refresh(
            raw, ip=client_ip(request), user_agent=user_agent(request)
        )
    except Unauthorized:
        await db.commit()  # persist family revocation on reuse detection
        clear_auth_cookies(response, ctx.settings)
        raise
    return _auth_response(response, ctx, user, tokens)


@router.post("/logout", response_model=Message)
async def logout(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    raw = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE)
    await AuthService(db, ctx).logout(raw)
    clear_auth_cookies(response, ctx.settings)
    return Message(detail="logged out")


@router.post("/logout-all", response_model=Message)
async def logout_all(
    response: Response,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    count = await AuthService(db, ctx).revoke_all_sessions(user)
    clear_auth_cookies(response, ctx.settings)
    return Message(detail=f"revoked {count} session(s)")


@router.post("/verify-email", response_model=UserOut)
async def verify_email(
    body: VerifyEmailRequest, db: AsyncSession = Depends(get_db), ctx: AppContext = Depends(get_ctx)
) -> User:
    return await AuthService(db, ctx).verify_email(body.token)


@router.post("/resend-verification", response_model=Message)
async def resend_verification(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    await AuthService(db, ctx).send_verification(user)
    return Message(
        detail="verification email sent" if not user.email_verified else "email already verified"
    )


@router.post("/forgot-password", response_model=Message, dependencies=[Depends(auth_rate_limit)])
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    await AuthService(db, ctx).forgot_password(body.email)
    return Message(detail="if that address exists, a reset link has been sent")


@router.post("/reset-password", response_model=Message)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    await AuthService(db, ctx).reset_password(body.token, body.password)
    return Message(detail="password updated, please sign in")


@router.post("/change-password", response_model=Message)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    ctx: AppContext = Depends(get_ctx),
) -> Message:
    await AuthService(db, ctx).change_password(user, body.current_password, body.new_password)
    clear_auth_cookies(response, ctx.settings)
    return Message(detail="password changed, please sign in again")
