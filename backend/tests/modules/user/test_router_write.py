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
async def admin(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str, User]:
    role = Role(code="user_admin", name="User Admin")
    db_session.add(role)
    await db_session.flush()

    await grant_perms(
        db_session,
        role.id,
        ["user:list", "user:read", "user:create", "user:update", "user:delete"],
    )

    u = User(
        email="useradmin@ex.com",
        password_hash=hash_password("Admin-pw1"),
        full_name="User Admin",
    )
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=role.id))
    await db_session.commit()

    token = await login(client_with_db, "useradmin@ex.com", "Admin-pw1")
    return client_with_db, token, u


async def test_create_user_201(admin: tuple[AsyncClient, str, User]) -> None:
    client, token, _ = admin
    payload = {
        "email": "newuser@ex.com",
        "password": "Str0ng-pass1",
        "fullName": "New User",
        "mustChangePassword": True,
    }
    resp = await client.post(
        "/api/v1/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "newuser@ex.com"
    assert body["mustChangePassword"] is True
    assert "passwordHash" not in body


async def test_create_user_weak_password_422(admin: tuple[AsyncClient, str, User]) -> None:
    client, token, _ = admin
    payload = {
        "email": "weak@ex.com",
        "password": "short",
        "fullName": "Weak Pass",
    }
    resp = await client.post(
        "/api/v1/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_update_user_patch(
    admin: tuple[AsyncClient, str, User], db_session: AsyncSession
) -> None:
    client, token, _ = admin
    target = User(
        email="patchme@ex.com",
        password_hash=hash_password("Admin-pw1"),
        full_name="Before Patch",
    )
    db_session.add(target)
    await db_session.commit()

    resp = await client.patch(
        f"/api/v1/users/{target.id}",
        json={"fullName": "New"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["fullName"] == "New"


async def test_delete_user_soft(
    admin: tuple[AsyncClient, str, User], db_session: AsyncSession
) -> None:
    client, token, _ = admin
    target = User(
        email="deleteme@ex.com",
        password_hash=hash_password("Admin-pw1"),
        full_name="To Delete",
    )
    db_session.add(target)
    await db_session.commit()

    resp = await client.delete(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204, resp.text

    await db_session.refresh(target)
    assert target.is_active is False


async def test_delete_self_blocked(admin: tuple[AsyncClient, str, User]) -> None:
    client, token, me = admin
    resp = await client.delete(
        f"/api/v1/users/{me.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body["code"] == "self-protection"
