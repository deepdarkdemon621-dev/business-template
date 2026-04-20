from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole
from tests.modules.user.conftest import grant_perms, login

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def admin_token(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str]:
    # Create an admin with user:list + user:read (global scope)
    role = Role(code="user_reader", name="UR")
    db_session.add(role)
    await db_session.flush()
    await grant_perms(db_session, role.id, ["user:list", "user:read"])
    u = User(email="admin@ex.com", password_hash=hash_password("pw-aaa111"), full_name="A")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=role.id))
    await db_session.commit()

    token = await login(client_with_db, "admin@ex.com", "pw-aaa111")
    return client_with_db, token


async def test_list_users_returns_page_shape(admin_token: tuple[AsyncClient, str]) -> None:
    client, token = admin_token
    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) >= {"items", "total", "page", "size", "hasNext"}


async def test_list_users_forbidden_without_perm(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> None:
    u = User(email="np@ex.com", password_hash=hash_password("pw-aaa111"), full_name="NP")
    db_session.add(u)
    await db_session.commit()
    token = await login(client_with_db, "np@ex.com", "pw-aaa111")
    resp = await client_with_db.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_list_users_is_active_filter(
    admin_token: tuple[AsyncClient, str], db_session: AsyncSession
) -> None:
    client, token = admin_token
    inactive = User(
        email="inactive@ex.com",
        password_hash=hash_password("pw-aaa111"),
        full_name="I",
        is_active=False,
    )
    db_session.add(inactive)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/users?is_active=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    for u in items:
        assert u["isActive"] is False


async def test_get_user_detail_includes_roles(
    admin_token: tuple[AsyncClient, str], db_session: AsyncSession
) -> None:
    client, token = admin_token
    target = User(email="target@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T")
    db_session.add(target)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/users/{target.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "target@ex.com"
    assert "roles" in body
    assert isinstance(body["roles"], list)
