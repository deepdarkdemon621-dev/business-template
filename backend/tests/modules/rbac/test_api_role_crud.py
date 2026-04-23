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


async def test_create_role_ok(admin_token: tuple[AsyncClient, str]) -> None:
    client, token = admin_token
    resp = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "code": "api_tester",
            "name": "API Tester",
            "permissions": [
                {"permissionCode": "user:read", "scope": "global"},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "api_tester"
    assert len(body["permissions"]) == 1


async def test_create_role_duplicate_code(
    admin_token: tuple[AsyncClient, str],
) -> None:
    client, token = admin_token
    resp = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "admin", "name": "Dup Admin"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "role.code-conflict"


async def test_create_role_forbidden_for_member(
    member_token: tuple[AsyncClient, str],
) -> None:
    client, token = member_token
    resp = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "nope", "name": "Nope"},
    )
    assert resp.status_code == 403


async def test_patch_role_metadata(admin_token: tuple[AsyncClient, str]) -> None:
    client, token = admin_token
    create = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "patch_me", "name": "Patch Me"},
    )
    assert create.status_code == 201, create.text
    role_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Patched"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Patched"


async def test_patch_builtin_metadata_refused(
    admin_token: tuple[AsyncClient, str], db_session: AsyncSession
) -> None:
    from app.modules.rbac.models import Role
    admin_role = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()

    client, token = admin_token
    resp = await client.patch(
        f"/api/v1/roles/{admin_role.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed Admin"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "role.builtin-locked"


async def test_delete_role_returns_cascade_count(
    admin_token: tuple[AsyncClient, str],
) -> None:
    client, token = admin_token
    create = await client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "del_me", "name": "Del Me"},
    )
    assert create.status_code == 201, create.text
    role_id = create.json()["id"]

    resp = await client.delete(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == role_id
    assert body["deletedUserRoles"] == 0


async def test_delete_builtin_refused(
    admin_token: tuple[AsyncClient, str], db_session: AsyncSession
) -> None:
    from app.modules.rbac.models import Role
    admin_role = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()

    client, token = admin_token
    resp = await client.delete(
        f"/api/v1/roles/{admin_role.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "role.builtin-locked"
