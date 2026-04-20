"""Integration tests for auth endpoints.

Runs against the real FastAPI app with the isolated `business_template_test`
Postgres DB. Schema is created once per session by the root conftest's
`_prepare_test_db` fixture (drop public schema + alembic upgrade head). Each
test runs inside a transaction that is rolled back on teardown (`db_session`),
so tests are independent without TRUNCATE dances.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def seeded_user(db_session: AsyncSession):
    """Insert a test user via the per-test rollback session."""
    from app.core.auth import hash_password
    from app.modules.auth.models import User

    user = User(
        email="test@example.com",
        password_hash=hash_password("ValidPass123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_login_success(client_with_db: AsyncClient, seeded_user):
    """POST /api/v1/auth/login with valid credentials returns 200 + tokens."""
    response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "ValidPass123"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "accessToken" in body
    assert "expiresIn" in body
    assert body["user"]["email"] == "test@example.com"
    assert "mustChangePassword" in body


async def test_login_bad_password(client_with_db: AsyncClient, seeded_user):
    """POST with wrong password returns 401 with code auth.invalid-credentials."""
    response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401, response.text
    body = response.json()
    assert body["code"] == "auth.invalid-credentials"


async def test_login_nonexistent_user(client_with_db: AsyncClient):
    """POST with an email that doesn't exist returns 401."""
    response = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "AnyPassword1"},
    )
    assert response.status_code == 401, response.text
    body = response.json()
    assert body["code"] == "auth.invalid-credentials"


async def test_profile_requires_auth(client_with_db: AsyncClient):
    """GET /api/v1/me/profile without a token returns 401 or 422."""
    response = await client_with_db.get("/api/v1/me/profile")
    assert response.status_code in (401, 422), response.text


async def test_login_then_profile(client_with_db: AsyncClient, seeded_user):
    """Login, then use the accessToken to fetch the profile."""
    # Step 1 — login
    login_resp = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "ValidPass123"},
    )
    assert login_resp.status_code == 200, login_resp.text
    access_token = login_resp.json()["accessToken"]

    # Step 2 — fetch profile with the token
    profile_resp = await client_with_db.get(
        "/api/v1/me/profile",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert profile_resp.status_code == 200, profile_resp.text
    body = profile_resp.json()
    assert body["email"] == "test@example.com"
    assert body["fullName"] == "Test User"
