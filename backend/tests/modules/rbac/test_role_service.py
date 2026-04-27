from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.errors import ProblemDetails
from app.modules.rbac import crud
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import RoleCreateIn, RolePermissionItem, RoleUpdateIn
from app.modules.rbac.service import RoleService


@pytest_asyncio.fixture
async def seeded_rbac(db_session):
    """No-op marker fixture: migrations seed admin + superadmin roles.

    Tests that depend on pre-seeded builtin roles use this fixture to
    communicate that dependency clearly.
    """
    return None


@pytest.mark.asyncio
async def test_role_service_create_ok(db_session, db_audit_ctx) -> None:
    svc = RoleService()
    role = await svc.create(
        db_session,
        RoleCreateIn(
            code="auditor",
            name="Auditor",
            permissions=[RolePermissionItem(permission_code="user:read", scope="global")],
        ),
    )
    await db_session.commit()
    assert role.code == "auditor"


@pytest.mark.asyncio
async def test_role_service_create_rejects_duplicate_code(db_session, db_audit_ctx) -> None:
    svc = RoleService()
    await svc.create(db_session, RoleCreateIn(code="dup_r", name="Dup R"))
    await db_session.commit()

    with pytest.raises(ProblemDetails) as exc:
        await svc.create(db_session, RoleCreateIn(code="dup_r", name="Dup R2"))
        await db_session.commit()
    assert exc.value.code == "role.code-conflict"
    assert exc.value.status == 409


@pytest.mark.asyncio
async def test_role_service_create_rejects_unknown_permission(db_session) -> None:
    svc = RoleService()
    with pytest.raises(ProblemDetails) as exc:
        await svc.create(
            db_session,
            RoleCreateIn(
                code="bad_perms",
                name="Bad",
                permissions=[
                    RolePermissionItem(permission_code="nonexistent:perm", scope="global")
                ],
            ),
        )
    assert exc.value.code == "role.permission-unknown"
    assert exc.value.status == 422


# ---------------------------------------------------------------------------
# E2: RoleService.update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_role_service_update_metadata_only(db_session, db_audit_ctx) -> None:
    svc = RoleService()
    role = await svc.create(db_session, RoleCreateIn(code="u_meta", name="Old Name"))
    await db_session.commit()

    updated = await svc.update(db_session, role, RoleUpdateIn(name="New Name"))
    await db_session.commit()
    assert updated.name == "New Name"
    assert updated.code == "u_meta"


@pytest.mark.asyncio
async def test_role_service_update_matrix_replaces_whole_set(db_session, db_audit_ctx) -> None:
    svc = RoleService()
    role = await svc.create(
        db_session,
        RoleCreateIn(
            code="u_matrix",
            name="Matrix",
            permissions=[
                RolePermissionItem(permission_code="user:read", scope="global"),
                RolePermissionItem(permission_code="user:list", scope="global"),
            ],
        ),
    )
    await db_session.commit()

    # Replace: remove user:list, add department:read@global, change user:read scope to dept_tree.
    await svc.update(
        db_session,
        role,
        RoleUpdateIn(
            permissions=[
                RolePermissionItem(permission_code="user:read", scope="dept_tree"),
                RolePermissionItem(permission_code="department:read", scope="global"),
            ],
        ),
    )
    await db_session.commit()

    _, items = await crud.get_role_with_permissions(db_session, role.id)
    by_code = {i.permission_code: i.scope.value for i in items}
    assert by_code == {"user:read": "dept_tree", "department:read": "global"}


@pytest.mark.asyncio
async def test_role_service_update_builtin_metadata_refused(db_session, seeded_rbac) -> None:
    svc = RoleService()
    admin = (await db_session.execute(select(Role).where(Role.code == "admin"))).scalar_one()

    with pytest.raises(ProblemDetails) as exc:
        await svc.update(db_session, admin, RoleUpdateIn(name="Renamed Admin"))
    assert exc.value.code == "role.builtin-locked"


@pytest.mark.asyncio
async def test_role_service_update_builtin_matrix_allowed(db_session, seeded_rbac, db_audit_ctx) -> None:
    svc = RoleService()
    admin = (await db_session.execute(select(Role).where(Role.code == "admin"))).scalar_one()

    # Matrix-only PATCH on builtin must succeed.
    await svc.update(
        db_session,
        admin,
        RoleUpdateIn(permissions=[RolePermissionItem(permission_code="user:read", scope="global")]),
    )
    await db_session.commit()
    _, items = await crud.get_role_with_permissions(db_session, admin.id)
    assert len(items) == 1


@pytest.mark.asyncio
async def test_role_service_update_superadmin_refused(db_session, seeded_rbac) -> None:
    svc = RoleService()
    superadmin = (
        await db_session.execute(select(Role).where(Role.is_superadmin.is_(True)))
    ).scalar_one()

    with pytest.raises(ProblemDetails) as exc:
        await svc.update(db_session, superadmin, RoleUpdateIn(name="X"))
    assert exc.value.code == "role.superadmin-locked"


# ---------------------------------------------------------------------------
# E3: RoleService.delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_role_service_delete_non_builtin_ok(db_session, db_audit_ctx) -> None:
    svc = RoleService()
    role = await svc.create(db_session, RoleCreateIn(code="del_r", name="Del R"))
    await db_session.commit()

    deleted = await svc.delete(db_session, role)
    await db_session.commit()
    assert deleted == 0


@pytest.mark.asyncio
async def test_role_service_delete_builtin_refused(db_session, seeded_rbac) -> None:
    svc = RoleService()
    admin = (await db_session.execute(select(Role).where(Role.code == "admin"))).scalar_one()
    with pytest.raises(ProblemDetails) as exc:
        await svc.delete(db_session, admin)
    assert exc.value.code == "role.builtin-locked"


@pytest.mark.asyncio
async def test_role_service_delete_superadmin_refused(db_session, seeded_rbac) -> None:
    svc = RoleService()
    superadmin = (
        await db_session.execute(select(Role).where(Role.is_superadmin.is_(True)))
    ).scalar_one()
    with pytest.raises(ProblemDetails) as exc:
        await svc.delete(db_session, superadmin)
    assert exc.value.code == "role.superadmin-locked"
