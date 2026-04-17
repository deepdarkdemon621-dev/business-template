"""Integration tests for auth endpoints.

Runs against the real FastAPI app with real PostgreSQL + Redis (via Docker).
Tables are created once for the module and truncated between tests.

All tests share a single event loop (loop_scope="module") so the module-level
SQLAlchemy engine pool and redis_pool remain valid across the entire test run.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import Base, async_session, engine
from app.main import app

# All async tests in this module share one event loop.
pytestmark = pytest.mark.asyncio(loop_scope="module")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="module", autouse=True, scope="module")
async def create_tables():
    """Create tables once for the module, drop them at the very end."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="module", autouse=True)
async def truncate_tables():
    """Truncate all auth tables before each test to give a clean slate."""
    yield
    async with engine.begin() as conn:
        # CASCADE handles the FK from user_sessions → users
        await conn.execute(
            __import__("sqlalchemy").text(
                "TRUNCATE TABLE user_sessions, users RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture(loop_scope="module")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(loop_scope="module")
async def seeded_user():
    """Insert a test user directly into the database."""
    from app.core.auth import hash_password
    from app.modules.auth.models import User

    async with async_session() as session:
        user = User(
            email="test@example.com",
            password_hash=hash_password("ValidPass123"),
            full_name="Test User",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_login_success(client: AsyncClient, seeded_user):
    """POST /api/v1/auth/login with valid credentials returns 200 + tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "ValidPass123"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "accessToken" in body
    assert "expiresIn" in body
    assert body["user"]["email"] == "test@example.com"
    assert "mustChangePassword" in body


async def test_login_bad_password(client: AsyncClient, seeded_user):
    """POST with wrong password returns 401 with code auth.invalid-credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401, response.text
    body = response.json()
    assert body["code"] == "auth.invalid-credentials"


async def test_login_nonexistent_user(client: AsyncClient):
    """POST with an email that doesn't exist returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "AnyPassword1"},
    )
    assert response.status_code == 401, response.text
    body = response.json()
    assert body["code"] == "auth.invalid-credentials"


async def test_profile_requires_auth(client: AsyncClient):
    """GET /api/v1/me/profile without a token returns 401 or 422."""
    response = await client.get("/api/v1/me/profile")
    assert response.status_code in (401, 422), response.text


async def test_login_then_profile(client: AsyncClient, seeded_user):
    """Login, then use the accessToken to fetch the profile."""
    # Step 1 — login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "ValidPass123"},
    )
    assert login_resp.status_code == 200, login_resp.text
    access_token = login_resp.json()["accessToken"]

    # Step 2 — fetch profile with the token
    profile_resp = await client.get(
        "/api/v1/me/profile",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert profile_resp.status_code == 200, profile_resp.text
    body = profile_resp.json()
    assert body["email"] == "test@example.com"
    assert body["fullName"] == "Test User"
