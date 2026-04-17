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
    from app.core.config import get_settings
    from jose import jwt

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
