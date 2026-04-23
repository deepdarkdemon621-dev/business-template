from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.rbac.crud import (
    count_role_permissions,
    count_role_users,
    create_role,
    delete_role,
    get_role_with_permissions,
    list_roles_with_counts,
)
from app.modules.rbac.models import Role, RolePermission, UserRole
from app.modules.rbac.schemas import RoleCreateIn, RolePermissionItem


@pytest.mark.asyncio
async def test_create_role_with_empty_matrix(db_session) -> None:
    payload = RoleCreateIn(code="viewer1", name="Viewer 1")
    role = await create_role(db_session, payload)
    await db_session.commit()
    assert role.code == "viewer1"
    assert role.is_builtin is False


@pytest.mark.asyncio
async def test_create_role_with_permissions(db_session) -> None:
    payload = RoleCreateIn(
        code="viewer2",
        name="Viewer 2",
        permissions=[
            RolePermissionItem(permission_code="user:read", scope="global"),
            RolePermissionItem(permission_code="department:read", scope="dept_tree"),
        ],
    )
    role = await create_role(db_session, payload)
    await db_session.commit()

    rps = (
        await db_session.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        )
    ).scalars().all()
    assert len(rps) == 2
    by_scope = {rp.scope for rp in rps}
    assert by_scope == {"global", "dept_tree"}


@pytest.mark.asyncio
async def test_get_role_with_permissions(db_session) -> None:
    admin = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()
    role, perm_items = await get_role_with_permissions(db_session, admin.id)
    assert role.code == "admin"
    # Plan 4 seeded admin with 15 perms; 0006 adds 3 more => 18.
    assert len(perm_items) >= 15


@pytest.mark.asyncio
async def test_count_role_users_and_permissions(db_session) -> None:
    admin = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()
    user_count = await count_role_users(db_session, admin.id)
    perm_count = await count_role_permissions(db_session, admin.id)
    assert user_count >= 0
    assert perm_count >= 15


@pytest.mark.asyncio
async def test_delete_role_cascades_via_fk(db_session) -> None:
    role = await create_role(
        db_session,
        RoleCreateIn(
            code="tmp_del",
            name="Tmp Del",
            permissions=[RolePermissionItem(permission_code="user:read", scope="global")],
        ),
    )
    await db_session.commit()
    role_id = role.id

    deleted_user_roles = await delete_role(db_session, role)
    await db_session.commit()
    assert deleted_user_roles == 0

    rps = (
        await db_session.execute(
            select(RolePermission).where(RolePermission.role_id == role_id)
        )
    ).scalars().all()
    assert rps == []


@pytest.mark.asyncio
async def test_list_roles_with_counts(db_session) -> None:
    rows = await list_roles_with_counts(db_session)
    by_code = {r["role"].code: r for r in rows}
    assert "admin" in by_code
    assert by_code["admin"]["user_count"] >= 0
    assert by_code["admin"]["permission_count"] >= 15
