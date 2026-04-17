from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    clear_failed_logins,
    create_access_token,
    denylist_token,
    hash_password,
    is_denylisted,
    is_locked_out,
    record_failed_login,
    verify_captcha,
    verify_password,
)
from app.core.config import get_settings
from app.core.email import send_email
from app.core.errors import ProblemDetails
from app.modules.auth import crud

_settings = get_settings()

_INVALID_CREDENTIALS = ProblemDetails(
    code="auth.invalid-credentials",
    status=401,
    detail="Invalid email or password.",
)


def _sign_jti(jti: str) -> str:
    return hmac.HMAC(_settings.secret_key.encode(), jti.encode(), hashlib.sha256).hexdigest()


def _verify_signed_jti(signed: str, jti: str) -> bool:
    return hmac.compare_digest(signed, _sign_jti(jti))


class AuthService:

    async def login(
        self,
        *,
        db: AsyncSession,
        redis: Redis,
        email: str,
        password: str,
        captcha: str | None,
        device_label: str | None,
        ip_address: str | None,
    ) -> dict:
        if await is_locked_out(redis, email):
            raise ProblemDetails(
                code="auth.locked-out",
                status=429,
                detail="Too many failed attempts. Try again later.",
            )

        if not await verify_captcha(captcha):
            raise ProblemDetails(
                code="auth.captcha-failed",
                status=400,
                detail="Captcha verification failed.",
            )

        user = await crud.get_user_by_email(db, email)
        if user is None:
            raise _INVALID_CREDENTIALS

        if not verify_password(password, user.password_hash):
            await record_failed_login(redis, email)
            raise _INVALID_CREDENTIALS

        if not user.is_active:
            raise _INVALID_CREDENTIALS

        await clear_failed_logins(redis, email)

        user_session = await crud.create_session(
            db,
            user_id=user.id,
            device_label=device_label,
            ip_address=ip_address,
            ttl_days=_settings.refresh_token_ttl_days,
        )

        access_token = create_access_token(
            sub=str(user.id),
            dept_id=str(user.department_id) if user.department_id else None,
        )

        return {
            "access_token": access_token,
            "expires_in": _settings.access_token_ttl_minutes * 60,
            "user": user,
            "must_change_password": user.must_change_password,
            "refresh_jti": str(user_session.id),
            "refresh_signed": _sign_jti(str(user_session.id)),
            "refresh_expires_at": user_session.expires_at,
        }
