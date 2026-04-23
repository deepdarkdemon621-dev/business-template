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
