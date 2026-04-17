import time

import pytest

from app.core.auth import (
    TokenPayload,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_returns_argon2_hash():
    h = hash_password("secret123")
    assert h.startswith("$argon2")


def test_verify_password_correct():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True


def test_verify_password_incorrect():
    h = hash_password("secret123")
    assert verify_password("wrong", h) is False


def test_create_and_decode_access_token():
    token = create_access_token(sub="user-1", role_ids=["r1"], dept_id="d1")
    payload = decode_access_token(token)
    assert isinstance(payload, TokenPayload)
    assert payload.sub == "user-1"
    assert payload.role_ids == ["r1"]
    assert payload.dept_id == "d1"
    assert payload.jti
    assert payload.exp > payload.iat


def test_decode_expired_token_raises():
    from jose import jwt

    from app.core.config import get_settings

    settings = get_settings()
    now = int(time.time()) - 100
    claims = {
        "sub": "user-1",
        "role_ids": [],
        "dept_id": None,
        "jti": "test-jti",
        "iat": now,
        "exp": now + 1,
    }
    token = jwt.encode(claims, settings.secret_key, algorithm="HS256")
    with pytest.raises(Exception):
        decode_access_token(token)


def test_decode_invalid_token_raises():
    with pytest.raises(Exception):
        decode_access_token("not-a-jwt")


from unittest.mock import AsyncMock

from app.core.auth import (
    clear_failed_logins,
    denylist_token,
    is_denylisted,
    is_locked_out,
    record_failed_login,
    verify_captcha,
)


@pytest.mark.asyncio
async def test_denylist_and_check():
    redis = AsyncMock()
    redis.exists.return_value = 0
    assert await is_denylisted(redis, "jti-1") is False
    redis.exists.return_value = 1
    assert await is_denylisted(redis, "jti-1") is True
    await denylist_token(redis, "jti-1", ttl_seconds=300)
    redis.set.assert_awaited_once_with("deny:jti-1", "1", ex=300)


@pytest.mark.asyncio
async def test_lockout_under_threshold():
    redis = AsyncMock()
    redis.get.return_value = "3"
    assert await is_locked_out(redis, "user@example.com") is False


@pytest.mark.asyncio
async def test_lockout_at_threshold():
    redis = AsyncMock()
    redis.get.return_value = "5"
    assert await is_locked_out(redis, "user@example.com") is True


@pytest.mark.asyncio
async def test_record_and_clear_failed_login():
    redis = AsyncMock()
    await record_failed_login(redis, "user@example.com")
    redis.incr.assert_awaited_once_with("login:fail:user@example.com")
    redis.expire.assert_awaited_once_with("login:fail:user@example.com", 900)
    await clear_failed_logins(redis, "user@example.com")
    redis.delete.assert_awaited_once_with("login:fail:user@example.com")


@pytest.mark.asyncio
async def test_captcha_hook_returns_true():
    assert await verify_captcha(None) is True
    assert await verify_captcha("any-token") is True


import sys
import types
from types import SimpleNamespace

from app.core.auth import get_current_user
from app.core.errors import ProblemDetails


class _StubUserModule:
    """
    Context manager that:
    1. Stubs app.modules.auth.models in sys.modules so the deferred import resolves.
    2. Makes `User` a MagicMock so attribute access (User.id) works without SQLAlchemy.
    3. Patches app.core.auth.select to return a MagicMock so SQLAlchemy's ORM
       coercion is bypassed entirely.
    """

    def __init__(self):
        from unittest.mock import MagicMock, patch

        # User must support attribute access like User.id — use MagicMock as the class
        self._fake_models = types.ModuleType("app.modules.auth.models")
        self._fake_models.User = MagicMock()  # type: ignore[attr-defined]
        self._fake_auth_pkg = types.ModuleType("app.modules.auth")
        self._patch_modules = patch.dict(
            sys.modules,
            {
                "app.modules.auth": self._fake_auth_pkg,
                "app.modules.auth.models": self._fake_models,
            },
        )
        # Replace `select` in auth.py so it never touches SQLAlchemy coercion
        self._patch_select = patch("app.core.auth.select", return_value=MagicMock())

    def __enter__(self):
        self._patch_modules.__enter__()
        self._patch_select.__enter__()
        return self

    def __exit__(self, *args):
        self._patch_select.__exit__(*args)
        self._patch_modules.__exit__(*args)


def _stub_user_module():
    """Return a context manager that stubs the User import and select() call."""
    return _StubUserModule()


def _make_execute_result(user):
    """
    Build a mock that looks like a SQLAlchemy Result.
    scalar_one_or_none() is synchronous in SQLAlchemy; MagicMock (not AsyncMock)
    is needed so calling it returns the value directly, not a coroutine.
    """
    from unittest.mock import MagicMock

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    return result_mock


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    token = create_access_token(sub="user-uuid-1")
    user = SimpleNamespace(id="user-uuid-1", is_active=True)

    session = AsyncMock()
    session.execute.return_value = _make_execute_result(user)

    with _stub_user_module():
        result = await get_current_user(
            authorization=f"Bearer {token}",
            session=session,
        )
    assert result.id == "user-uuid-1"


@pytest.mark.asyncio
async def test_get_current_user_missing_bearer():
    session = AsyncMock()
    with pytest.raises(ProblemDetails) as ei:
        await get_current_user(authorization="bad-header", session=session)
    assert ei.value.code == "auth.invalid-token"


@pytest.mark.asyncio
async def test_get_current_user_inactive_user():
    token = create_access_token(sub="user-uuid-2")
    user = SimpleNamespace(id="user-uuid-2", is_active=False)

    session = AsyncMock()
    session.execute.return_value = _make_execute_result(user)

    with _stub_user_module(), pytest.raises(ProblemDetails) as ei:
        await get_current_user(
            authorization=f"Bearer {token}",
            session=session,
        )
    assert ei.value.code == "auth.inactive-user"


@pytest.mark.asyncio
async def test_get_current_user_user_not_found():
    token = create_access_token(sub="nonexistent")

    session = AsyncMock()
    session.execute.return_value = _make_execute_result(None)

    with _stub_user_module(), pytest.raises(ProblemDetails) as ei:
        await get_current_user(
            authorization=f"Bearer {token}",
            session=session,
        )
    assert ei.value.code == "auth.invalid-token"
