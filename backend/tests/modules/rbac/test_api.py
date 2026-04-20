"""Integration tests for RBAC endpoints.

Same pattern as `tests/modules/auth/test_auth_endpoints.py`: AsyncClient +
client_with_db fixture, login via POST /api/v1/auth/login, send the bearer
token on subsequent requests.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


async def _login(client: AsyncClient, email: str, password: str) -> str:
    """POST /api/v1/auth/login, return accessToken."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["accessToken"]


@pytest_asyncio.fixture
async def plain_user(db_session: AsyncSession) -> User:
    """Authenticated user with no roles."""
    user = User(
        email="plain@example.com",
        password_hash=hash_password("ValidPass123"),
        full_name="Plain User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def superadmin_user(db_session: AsyncSession) -> User:
    """User with superadmin role attached via UserRole row."""
    user = User(
        email="sa@example.com",
        password_hash=hash_password("ValidPass123"),
        full_name="Super Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(select(Role).where(Role.code == "superadmin"))
    sa_role = result.scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=sa_role.id))
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# GET /me/permissions
# ---------------------------------------------------------------------------


async def test_me_permissions_superadmin(client_with_db: AsyncClient, superadmin_user: User):
    token = await _login(client_with_db, "sa@example.com", "ValidPass123")
    resp = await client_with_db.get(
        "/api/v1/me/permissions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["isSuperadmin"] is True
    assert body["permissions"] == {}


async def test_me_permissions_plain_user(client_with_db: AsyncClient, plain_user: User):
    token = await _login(client_with_db, "plain@example.com", "ValidPass123")
    resp = await client_with_db.get(
        "/api/v1/me/permissions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["isSuperadmin"] is False
    assert body["permissions"] == {}


async def test_me_permissions_unauthenticated(client_with_db: AsyncClient):
    resp = await client_with_db.get("/api/v1/me/permissions")
    assert resp.status_code in (401, 422), resp.text


# ---------------------------------------------------------------------------
# GET /departments
# ---------------------------------------------------------------------------


async def test_departments_superadmin_lists_all(client_with_db: AsyncClient, superadmin_user: User):
    token = await _login(client_with_db, "sa@example.com", "ValidPass123")
    resp = await client_with_db.get(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    # Migration seeds at least one root (depth=0) department.
    assert isinstance(items, list)
    assert len(items) >= 1
    assert any(d["depth"] == 0 for d in items)


async def test_departments_forbidden_for_plain_user(client_with_db: AsyncClient, plain_user: User):
    token = await _login(client_with_db, "plain@example.com", "ValidPass123")
    resp = await client_with_db.get(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text
