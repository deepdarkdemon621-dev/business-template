from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from jose import JWTError, jwt
from passlib.context import CryptContext

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
