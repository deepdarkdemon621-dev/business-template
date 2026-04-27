from __future__ import annotations

import hashlib
import hmac
import secrets
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
from app.core.database import async_session as _audit_session_factory
from app.core.email import send_email
from app.core.errors import ProblemDetails
from app.modules.audit.service import audit
from app.modules.auth import crud

_settings = get_settings()


async def _emit_failed_login_independently(email: str, reason: str) -> None:
    """Persist auth.login_failed in its own transaction so the raise that
    follows doesn't roll it back. The contextvar carries IP/UA across.
    """
    async with _audit_session_factory() as fresh:
        await audit.login_failed(fresh, email, reason)
        await fresh.commit()


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
            await _emit_failed_login_independently(email, "locked")
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
            await _emit_failed_login_independently(email, "unknown_email")
            raise _INVALID_CREDENTIALS

        if not verify_password(password, user.password_hash):
            await record_failed_login(redis, email)
            await _emit_failed_login_independently(email, "bad_password")
            raise _INVALID_CREDENTIALS

        if not user.is_active:
            await _emit_failed_login_independently(email, "disabled_account")
            raise _INVALID_CREDENTIALS

        await clear_failed_logins(redis, email)

        user.last_login_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(user)
        await audit.login_succeeded(db, user)

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

    @staticmethod
    def _sign_jti(jti: str) -> str:
        return _sign_jti(jti)

    async def refresh(
        self,
        *,
        db: AsyncSession,
        redis: Redis,
        jti: str,
        signed: str,
    ) -> dict:
        if not _verify_signed_jti(signed, jti):
            raise ProblemDetails(
                code="auth.invalid-token",
                status=401,
                detail="Invalid refresh token.",
            )
        if await is_denylisted(redis, jti):
            raise ProblemDetails(
                code="auth.invalid-token",
                status=401,
                detail="Token has been revoked.",
            )
        session_obj = await crud.get_session_by_id(db, uuid.UUID(jti))
        if session_obj is None:
            raise ProblemDetails(
                code="auth.invalid-token",
                status=401,
                detail="Session not found.",
            )
        now = datetime.now(tz=UTC)
        if session_obj.expires_at < now:
            raise ProblemDetails(
                code="auth.invalid-token",
                status=401,
                detail="Session expired.",
            )
        idle_deadline = session_obj.last_used_at + timedelta(
            minutes=_settings.refresh_token_idle_minutes
        )
        if idle_deadline < now:
            raise ProblemDetails(
                code="auth.invalid-token",
                status=401,
                detail="Session idle timeout.",
            )
        remaining = int((session_obj.expires_at - now).total_seconds())
        await denylist_token(redis, jti, ttl_seconds=max(remaining, 1))
        new_session = await crud.create_session(
            db,
            user_id=session_obj.user_id,
            device_label=session_obj.device_label,
            ip_address=session_obj.ip_address,
            ttl_days=_settings.refresh_token_ttl_days,
        )
        await crud.delete_session(db, session_obj.id)
        access_token = create_access_token(
            sub=str(session_obj.user_id),
            dept_id=str(session_obj.user.department_id) if session_obj.user.department_id else None,
        )
        return {
            "access_token": access_token,
            "expires_in": _settings.access_token_ttl_minutes * 60,
            "refresh_jti": str(new_session.id),
            "refresh_signed": _sign_jti(str(new_session.id)),
            "refresh_expires_at": new_session.expires_at,
        }

    async def logout(
        self,
        *,
        db: AsyncSession,
        redis: Redis,
        jti: str,
    ) -> None:
        session_obj = await crud.get_session_by_id(db, uuid.UUID(jti))
        if session_obj:
            from app.modules.auth.models import User

            user = await db.get(User, session_obj.user_id)
            if user is not None:
                await audit.logout(db, user)
            remaining = int((session_obj.expires_at - datetime.now(tz=UTC)).total_seconds())
            await denylist_token(redis, jti, ttl_seconds=max(remaining, 1))
            await crud.delete_session(db, session_obj.id)

    async def change_password(
        self,
        *,
        db: AsyncSession,
        user,
        current_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise ProblemDetails(
                code="auth.invalid-credentials",
                status=401,
                detail="Current password is incorrect.",
            )
        new_hash = hash_password(new_password)
        await crud.update_user_password(db, user, new_hash)
        await audit.password_changed(db, user)

    async def request_password_reset(
        self,
        *,
        db: AsyncSession,
        redis: Redis,
        email: str,
    ) -> None:
        user = await crud.get_user_by_email(db, email)
        if user is None:
            return
        token = secrets.token_urlsafe(32)
        await redis.set(f"reset:{token}", str(user.id), ex=3600)
        origins = _settings.allowed_origins.split(",")
        reset_link = f"{origins[0].strip()}/password-reset/confirm?token={token}"
        await audit.password_reset_requested(db, user)
        await send_email(
            to=email,
            subject="Password Reset",
            template="password_reset",
            context={"reset_link": reset_link, "ttl_hours": 1},
        )

    async def confirm_password_reset(
        self,
        *,
        db: AsyncSession,
        redis: Redis,
        token: str,
        new_password: str,
    ) -> None:
        user_id = await redis.get(f"reset:{token}")
        if user_id is None:
            raise ProblemDetails(
                code="auth.reset-token-invalid",
                status=400,
                detail="Reset token is invalid or expired.",
            )
        from sqlalchemy import select

        from app.modules.auth.models import User

        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if user is None:
            raise ProblemDetails(
                code="auth.reset-token-invalid",
                status=400,
                detail="User not found.",
            )
        new_hash = hash_password(new_password)
        await crud.update_user_password(db, user, new_hash)
        await redis.delete(f"reset:{token}")
        await audit.password_reset_consumed(db, user)
        sessions = await crud.delete_user_sessions(db, user.id)
        now = datetime.now(tz=UTC)
        for s in sessions:
            remaining = int((s.expires_at - now).total_seconds())
            if remaining > 0:
                await denylist_token(redis, str(s.id), ttl_seconds=remaining)

    async def list_sessions(
        self,
        *,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list:
        return await crud.get_user_sessions(db, user_id)

    async def revoke_session(
        self,
        *,
        db: AsyncSession,
        redis: Redis,
        jti: uuid.UUID,
        current_jti: uuid.UUID,
    ) -> None:
        if jti == current_jti:
            raise ProblemDetails(
                code="auth.cannot-revoke-current",
                status=400,
                detail="Use logout to end your current session.",
            )
        session_obj = await crud.get_session_by_id(db, jti)
        if session_obj is None:
            raise ProblemDetails(
                code="auth.invalid-token",
                status=404,
                detail="Session not found.",
            )
        remaining = int((session_obj.expires_at - datetime.now(tz=UTC)).total_seconds())
        await denylist_token(redis, str(jti), ttl_seconds=max(remaining, 1))
        await crud.delete_session(db, jti)
        from app.modules.auth.models import User

        user = await db.get(User, session_obj.user_id)
        if user is not None:
            await audit.session_revoked(db, user, session_id=jti, by_admin=False)
