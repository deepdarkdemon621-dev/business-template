import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rbac.models import Department


@pytest.mark.asyncio
async def test_department_insert_and_path(db_session: AsyncSession):
    root = Department(name="Root", path="/root-uuid", depth=0, parent_id=None)
    db_session.add(root)
    await db_session.flush()
    result = await db_session.execute(select(Department).where(Department.id == root.id))
    fetched = result.scalar_one()
    assert fetched.name == "Root"
    assert fetched.depth == 0
    assert fetched.is_active is True


@pytest.mark.asyncio
async def test_permission_code_unique(db_session: AsyncSession):
    from app.modules.rbac.models import Permission
    # Use a code outside the 15-seed set so this test works against a pre-seeded DB.
    p = Permission(code="custom:read", resource="custom", action="read", description="Custom read perm")
    db_session.add(p)
    await db_session.flush()
    assert p.id is not None


@pytest.mark.asyncio
async def test_role_is_superadmin_defaults_false(db_session: AsyncSession):
    from app.modules.rbac.models import Role
    r = Role(code="custom", name="Custom", is_builtin=False)
    db_session.add(r)
    await db_session.flush()
    assert r.is_superadmin is False
    assert r.is_builtin is False


@pytest.mark.asyncio
async def test_seed_inserts_15_permissions(db_session: AsyncSession):
    from app.modules.rbac.models import Permission

    result = await db_session.execute(select(func.count(Permission.id)))
    assert result.scalar() == 15


@pytest.mark.asyncio
async def test_seed_roles(db_session: AsyncSession):
    from app.modules.rbac.models import Role, RolePermission

    result = await db_session.execute(select(Role).where(Role.code == "superadmin"))
    sa_role = result.scalar_one()
    assert sa_role.is_superadmin is True

    result = await db_session.execute(select(Role).where(Role.code == "admin"))
    admin = result.scalar_one()
    result = await db_session.execute(
        select(func.count(RolePermission.permission_id)).where(
            RolePermission.role_id == admin.id
        )
    )
    assert result.scalar() == 15

    result = await db_session.execute(select(Role).where(Role.code == "member"))
    member = result.scalar_one()
    result = await db_session.execute(
        select(func.count(RolePermission.permission_id)).where(
            RolePermission.role_id == member.id
        )
    )
    assert result.scalar() == 7
