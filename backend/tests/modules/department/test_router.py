from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_departments_requires_auth(client_with_db: AsyncClient) -> None:
    r = await client_with_db.get("/api/v1/departments")
    assert r.status_code in (401, 422)


async def test_tree_endpoint_returns_nested_children(
    admin_client: AsyncClient, seed_department_tree: dict
) -> None:
    r = await admin_client.get("/api/v1/departments/tree")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert all("children" in node for node in body)


async def test_create_department(
    admin_client: AsyncClient, seed_department_tree: dict
) -> None:
    root_id = seed_department_tree["root_id"]
    r = await admin_client.post(
        "/api/v1/departments", json={"name": "NewChild", "parentId": str(root_id)}
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "NewChild"
    assert body["parentId"] == str(root_id)


async def test_rename_department(
    admin_client: AsyncClient, seed_department_tree: dict
) -> None:
    leaf_id = seed_department_tree["leaf_id"]
    r = await admin_client.patch(
        f"/api/v1/departments/{leaf_id}", json={"name": "Renamed"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Renamed"


async def test_move_department(
    admin_client: AsyncClient, seed_department_tree: dict
) -> None:
    leaf_id = seed_department_tree["leaf_id"]
    other_root_id = seed_department_tree["other_root_id"]
    r = await admin_client.post(
        f"/api/v1/departments/{leaf_id}/move",
        json={"newParentId": str(other_root_id)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["parentId"] == str(other_root_id)


async def test_move_into_self_rejected(
    admin_client: AsyncClient, seed_department_tree: dict
) -> None:
    leaf_id = seed_department_tree["leaf_id"]
    r = await admin_client.post(
        f"/api/v1/departments/{leaf_id}/move",
        json={"newParentId": str(leaf_id)},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "department.self-parent"


async def test_delete_department_with_children_rejected(
    admin_client: AsyncClient, seed_department_tree: dict
) -> None:
    root_id = seed_department_tree["root_id"]
    r = await admin_client.delete(f"/api/v1/departments/{root_id}")
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "department.has-children"


async def test_delete_leaf_ok(
    admin_client: AsyncClient, seed_department_tree: dict
) -> None:
    leaf_id = seed_department_tree["leaf_id"]
    r = await admin_client.delete(f"/api/v1/departments/{leaf_id}")
    assert r.status_code == 204, r.text
