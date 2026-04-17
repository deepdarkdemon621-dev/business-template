from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ProblemDetails

_pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")
_settings = get_settings()


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


@dataclass(frozen=True)
class TokenPayload:
    sub: str
    role_ids: list[str]
    dept_id: str | None
    jti: str
    iat: int
    exp: int


def create_access_token(
    sub: str,
    role_ids: list[str] | None = None,
    dept_id: str | None = None,
) -> str:
    now = int(time.time())
    claims = {
        "sub": sub,
        "role_ids": role_ids or [],
        "dept_id": dept_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + _settings.access_token_ttl_minutes * 60,
    }
    return jwt.encode(claims, _settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> TokenPayload:
    try:
        data = jwt.decode(token, _settings.secret_key, algorithms=["HS256"])
        return TokenPayload(
            sub=data["sub"],
            role_ids=data.get("role_ids", []),
            dept_id=data.get("dept_id"),
            jti=data["jti"],
            iat=data["iat"],
            exp=data["exp"],
        )
    except (JWTError, KeyError) as e:
        raise ProblemDetails(
            code="auth.invalid-token",
            status=401,
            detail="Invalid or expired token.",
        ) from e


async def denylist_token(redis: Redis, jti: str, ttl_seconds: int) -> None:
    await redis.set(f"deny:{jti}", "1", ex=ttl_seconds)


async def is_denylisted(redis: Redis, jti: str) -> bool:
    return bool(await redis.exists(f"deny:{jti}"))


async def record_failed_login(redis: Redis, email: str) -> None:
    key = f"login:fail:{email}"
    await redis.incr(key)
    await redis.expire(key, 900)


async def is_locked_out(redis: Redis, email: str) -> bool:
    count = await redis.get(f"login:fail:{email}")
    return int(count or 0) >= 5


async def clear_failed_logins(redis: Redis, email: str) -> None:
    await redis.delete(f"login:fail:{email}")


async def verify_captcha(token: str | None) -> bool:
    return True


async def get_current_user(
    authorization: str,
    session: AsyncSession,
) -> Any:
    if not authorization.startswith("Bearer "):
        raise ProblemDetails(
            code="auth.invalid-token",
            status=401,
            detail="Missing or malformed Authorization header.",
        )

    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)

    # Deferred import to avoid circular deps (User model in modules/auth)
    from app.modules.auth.models import User

    result = await session.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()
    if user is None:
        raise ProblemDetails(
            code="auth.invalid-token",
            status=401,
            detail="User not found.",
        )
    if not user.is_active:
        raise ProblemDetails(
            code="auth.inactive-user",
            status=403,
            detail="User account is disabled.",
        )
    return user
