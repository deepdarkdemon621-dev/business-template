from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.errors import ProblemDetails
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import RoleCreateIn, RolePermissionItem
from app.modules.rbac.service import RoleService


@pytest_asyncio.fixture
async def seeded_rbac(db_session):
    """No-op marker fixture: migrations seed admin + superadmin roles.

    Tests that depend on pre-seeded builtin roles use this fixture to
    communicate that dependency clearly.
    """
    return None


@pytest.mark.asyncio
async def test_role_service_create_ok(db_session) -> None:
    svc = RoleService()
    role = await svc.create(
        db_session,
        RoleCreateIn(
            code="auditor",
            name="Auditor",
            permissions=[
                RolePermissionItem(permission_code="user:read", scope="global")
            ],
        ),
    )
    await db_session.commit()
    assert role.code == "auditor"


@pytest.mark.asyncio
async def test_role_service_create_rejects_duplicate_code(db_session) -> None:
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
