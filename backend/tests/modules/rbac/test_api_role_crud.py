from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_list_roles_returns_counts(
    admin_token: tuple[AsyncClient, str],
) -> None:
    client, token = admin_token
    resp = await client.get(
        "/api/v1/roles", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    admin_row = next(r for r in body["items"] if r["code"] == "admin")
    assert "userCount" in admin_row
    assert "permissionCount" in admin_row
    assert "updatedAt" in admin_row
    assert admin_row["userCount"] >= 1
    assert admin_row["permissionCount"] >= 15


async def test_get_role_detail(
    admin_token: tuple[AsyncClient, str], db_session: AsyncSession
) -> None:
    from app.modules.rbac.models import Role
    admin = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()

    client, token = admin_token
    resp = await client.get(
        f"/api/v1/roles/{admin.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == "admin"
    assert isinstance(body["permissions"], list)
    assert any(p["permissionCode"] == "user:read" for p in body["permissions"])


async def test_get_role_404(admin_token: tuple[AsyncClient, str]) -> None:
    client, token = admin_token
    resp = await client.get(
        f"/api/v1/roles/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "role.not-found"


async def test_list_permissions(admin_token: tuple[AsyncClient, str]) -> None:
    client, token = admin_token
    resp = await client.get(
        "/api/v1/permissions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    codes = {p["code"] for p in body["items"]}
    assert "user:read" in codes
    assert "role:create" in codes
