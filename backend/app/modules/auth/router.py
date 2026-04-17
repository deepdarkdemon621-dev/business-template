from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status
from redis.asyncio import Redis
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_session
from app.core.pagination import Page, PageQuery, paginate
from app.core.permissions import public_endpoint
from app.core.redis import get_redis
from app.modules.auth.models import UserSession
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    SessionRead,
    TokenResponse,
    UserRead,
)
from app.modules.auth.service import AuthService

_settings = get_settings()
_COOKIE_NAME = "refresh_token"
_COOKIE_SIG_NAME = "refresh_sig"

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_refresh_cookie(response: Response, jti: str, signed: str, expires_at) -> None:
    common = {
        "httponly": True,
        "secure": _settings.app_env != "dev",
        "samesite": "strict",
        "path": "/api/v1/auth",
    }
    max_age = int((expires_at - datetime.now(UTC)).total_seconds())
    response.set_cookie(_COOKIE_NAME, jti, max_age=max_age, **common)
    response.set_cookie(_COOKIE_SIG_NAME, signed, max_age=max_age, **common)


def _clear_refresh_cookie(response: Response) -> None:
    common = {
        "httponly": True,
        "secure": _settings.app_env != "dev",
        "samesite": "strict",
        "path": "/api/v1/auth",
    }
    response.delete_cookie(_COOKIE_NAME, **common)
    response.delete_cookie(_COOKIE_SIG_NAME, **common)


# ---------------------------------------------------------------------------
# FastAPI dependency wrappers
# ---------------------------------------------------------------------------


async def _current_user(
    authorization: Annotated[str, Header()] = "",
    session: AsyncSession = Depends(get_session),
):
    return await get_current_user(authorization, session)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/auth/login", response_model=LoginResponse, dependencies=[Depends(public_endpoint)])
@limiter.limit("20/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> LoginResponse:
    svc = AuthService()
    device_label = request.headers.get("X-Device-Label")
    ip_address = request.client.host if request.client else None
    result = await svc.login(
        db=session,
        redis=redis,
        email=body.email,
        password=body.password,
        captcha=body.captcha,
        device_label=device_label,
        ip_address=ip_address,
    )
    await session.commit()
    _set_refresh_cookie(
        response,
        jti=result["refresh_jti"],
        signed=result["refresh_signed"],
        expires_at=result["refresh_expires_at"],
    )
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
        user=UserRead.model_validate(result["user"]),
        must_change_password=result["must_change_password"],
    )


@router.post("/auth/refresh", response_model=TokenResponse, dependencies=[Depends(public_endpoint)])
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    refresh_token: Annotated[str | None, Cookie()] = None,
    refresh_sig: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    from app.core.errors import ProblemDetails

    if not refresh_token or not refresh_sig:
        raise ProblemDetails(
            code="auth.invalid-token",
            status=401,
            detail="Missing refresh token cookies.",
        )
    svc = AuthService()
    result = await svc.refresh(
        db=session,
        redis=redis,
        jti=refresh_token,
        signed=refresh_sig,
    )
    await session.commit()
    _set_refresh_cookie(
        response,
        jti=result["refresh_jti"],
        signed=result["refresh_signed"],
        expires_at=result["refresh_expires_at"],
    )
    return TokenResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    current_user=Depends(_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    svc = AuthService()
    jti = refresh_token or ""
    if jti:
        await svc.logout(db=session, redis=redis, jti=jti)
        await session.commit()
    _clear_refresh_cookie(response)


@router.get("/me/profile", response_model=UserRead)
async def get_profile(current_user=Depends(_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChangeRequest,
    current_user=Depends(_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = AuthService()
    await svc.change_password(
        db=session,
        user=current_user,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    await session.commit()


@router.get("/me/sessions", response_model=Page[SessionRead])
async def list_sessions(
    pq: Annotated[PageQuery, Depends()],
    current_user=Depends(_current_user),
    session: AsyncSession = Depends(get_session),
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Page[SessionRead]:
    stmt = (
        select(UserSession)
        .where(UserSession.user_id == current_user.id)
        .order_by(UserSession.last_used_at.desc())
    )
    raw_page = await paginate(session, stmt, pq)
    current_jti = refresh_token or ""
    items = [
        SessionRead(
            id=s.id,
            device_label=s.device_label,
            ip_address=s.ip_address,
            created_at=s.created_at,
            last_used_at=s.last_used_at,
            expires_at=s.expires_at,
            is_current=(str(s.id) == current_jti),
        )
        for s in raw_page.items
    ]
    return Page[SessionRead](
        items=items,
        total=raw_page.total,
        page=raw_page.page,
        size=raw_page.size,
        has_next=raw_page.has_next,
    )


@router.delete("/me/sessions/{jti}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    jti: uuid.UUID,
    current_user=Depends(_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    current_jti = uuid.UUID(refresh_token) if refresh_token else uuid.uuid4()
    svc = AuthService()
    await svc.revoke_session(
        db=session,
        redis=redis,
        jti=jti,
        current_jti=current_jti,
    )
    await session.commit()


@router.post(
    "/auth/password-reset/request",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(public_endpoint)],
)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    svc = AuthService()
    await svc.request_password_reset(db=session, redis=redis, email=body.email)
    return {"detail": "If that email exists, a reset link has been sent."}


@router.post(
    "/auth/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(public_endpoint)],
)
async def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> None:
    svc = AuthService()
    await svc.confirm_password_reset(
        db=session,
        redis=redis,
        token=body.token,
        new_password=body.new_password,
    )
    await session.commit()
