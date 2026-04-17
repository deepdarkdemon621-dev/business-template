from app.core.auth import hash_password, verify_password


def test_hash_password_returns_argon2_hash():
    h = hash_password("secret123")
    assert h.startswith("$argon2")


def test_verify_password_correct():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True


def test_verify_password_incorrect():
    h = hash_password("secret123")
    assert verify_password("wrong", h) is False
