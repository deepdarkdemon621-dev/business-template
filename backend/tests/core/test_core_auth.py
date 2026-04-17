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
