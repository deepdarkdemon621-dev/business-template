from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole
from tests.modules.user.conftest import grant_perms, login

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def assigner(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str, User, Role]:
    target_role = Role(code="target_role", name="TR")
    admin_role = Role(code="user_assigner", name="UA")
    db_session.add_all([target_role, admin_role])
    await db_session.flush()

    await grant_perms(
        db_session, admin_role.id, ["user:list", "user:read", "user:assign", "role:list"]
    )

    u = User(email="ag@ex.com", password_hash=hash_password("pw-aaa111"), full_name="AG")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=admin_role.id))
    await db_session.commit()

    token = await login(client_with_db, "ag@ex.com", "pw-aaa111")
    return client_with_db, token, u, target_role


async def test_list_roles(assigner: tuple[AsyncClient, str, User, Role]) -> None:
    client, token, _, _ = assigner
    resp = await client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    codes = {r["code"] for r in body["items"]}
    assert "target_role" in codes


async def test_assign_role_idempotent(
    assigner: tuple[AsyncClient, str, User, Role], db_session: AsyncSession
) -> None:
    client, token, _, role = assigner
    target = User(email="tgt@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T")
    db_session.add(target)
    await db_session.commit()

    for _ in range(2):
        resp = await client.post(
            f"/api/v1/users/{target.id}/roles/{role.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    count = (
        await db_session.execute(
            select(func.count())
            .select_from(UserRole)
            .where(UserRole.user_id == target.id, UserRole.role_id == role.id)
        )
    ).scalar_one()
    assert count == 1


async def test_revoke_role_missing_404(
    assigner: tuple[AsyncClient, str, User, Role], db_session: AsyncSession
) -> None:
    client, token, _, role = assigner
    target = User(email="tgt2@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T2")
    db_session.add(target)
    await db_session.commit()

    resp = await client.delete(
        f"/api/v1/users/{target.id}/roles/{role.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "role-not-assigned"
