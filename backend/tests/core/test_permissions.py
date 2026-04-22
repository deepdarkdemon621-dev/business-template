import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import SUPERADMIN_ALL, apply_scope, get_user_permissions
from app.modules.auth.models import User
from app.modules.rbac.constants import ScopeEnum
from app.modules.rbac.models import (
    Department,
    Permission,
    Role,
    RolePermission,
    UserRole,
)


@pytest.mark.asyncio
async def test_get_user_permissions_superadmin_returns_sentinel(
    db_session: AsyncSession,
):
    user = User(
        id=uuid.uuid4(),
        email="s@example.com",
        full_name="S",
        password_hash="x",
        is_active=True,
    )
    db_session.add(user)
    superadmin_role = (
        await db_session.execute(select(Role).where(Role.code == "superadmin"))
    ).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=superadmin_role.id))
    await db_session.flush()

    result = await get_user_permissions(db_session, user)
    assert result is SUPERADMIN_ALL


@pytest.mark.asyncio
async def test_get_user_permissions_admin_role_returns_dict_with_global(
    db_session: AsyncSession,
):
    """Admin role grants all non-superadmin codes at scope=global. Fold should yield dict[str, ScopeEnum]."""
    from app.modules.rbac.constants import ScopeEnum

    user = User(
        id=uuid.uuid4(),
        email="a@example.com",
        full_name="A",
        password_hash="x",
        is_active=True,
    )
    db_session.add(user)
    admin_role = (await db_session.execute(select(Role).where(Role.code == "admin"))).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))
    await db_session.flush()

    result = await get_user_permissions(db_session, user)
    assert result is not SUPERADMIN_ALL
    assert isinstance(result, dict)
    # Use >= to avoid requiring every future migration to bump this hardcoded number.
    assert len(result) >= 16
    assert result["user:read"] == ScopeEnum.GLOBAL
    assert result["user:assign"] == ScopeEnum.GLOBAL


def test_require_perm_returns_callable():
    from app.core.permissions import require_perm

    dep = require_perm("user:delete")
    assert callable(dep)


@pytest.mark.asyncio
async def test_apply_scope_global_no_filter(db_session: AsyncSession):
    """Superadmin -> no added WHERE, stmt unchanged."""
    from sqlalchemy import select as sa_select

    from app.core.permissions import apply_scope, get_user_permissions

    u = User(
        id=uuid.uuid4(),
        email="ag@example.com",
        full_name="AG",
        password_hash="x",
        is_active=True,
    )
    db_session.add(u)
    sr = (await db_session.execute(sa_select(Role).where(Role.code == "superadmin"))).scalar_one()
    db_session.add(UserRole(user_id=u.id, role_id=sr.id))
    await db_session.flush()

    perms = await get_user_permissions(db_session, u)
    stmt = sa_select(User)
    filtered = apply_scope(stmt, u, "user:list", User, perms)
    assert str(filtered.compile()) == str(stmt.compile())


@pytest.mark.asyncio
async def test_load_in_scope_returns_row_when_found(db_session: AsyncSession):
    """Superadmin can load any user by id (no scope restriction)."""
    from sqlalchemy import select as sa_select

    from app.core.permissions import get_user_permissions, load_in_scope

    admin = User(
        id=uuid.uuid4(),
        email="sa@example.com",
        full_name="SA",
        password_hash="x",
        is_active=True,
    )
    target = User(
        id=uuid.uuid4(),
        email="t@example.com",
        full_name="T",
        password_hash="x",
        is_active=True,
    )
    db_session.add_all([admin, target])
    sr = (await db_session.execute(sa_select(Role).where(Role.code == "superadmin"))).scalar_one()
    db_session.add(UserRole(user_id=admin.id, role_id=sr.id))
    await db_session.flush()

    perms = await get_user_permissions(db_session, admin)
    row = await load_in_scope(db_session, User, target.id, admin, "user:read", perms)
    assert row.id == target.id


@pytest.mark.asyncio
async def test_load_in_scope_404_when_out_of_scope(db_session: AsyncSession):
    """User with no permission for user:read on another user -> 404."""
    from app.core.errors import ProblemDetails
    from app.core.permissions import load_in_scope

    me = User(
        id=uuid.uuid4(),
        email="me@example.com",
        full_name="Me",
        password_hash="x",
        is_active=True,
    )
    other = User(
        id=uuid.uuid4(),
        email="o@example.com",
        full_name="O",
        password_hash="x",
        is_active=True,
    )
    db_session.add_all([me, other])
    await db_session.flush()

    # Me has no roles -> perms is {}, no user:read key. apply_scope returns WHERE false.
    perms: dict[str, object] = {}
    with pytest.raises(ProblemDetails) as exc_info:
        await load_in_scope(db_session, User, other.id, me, "user:read", perms)
    assert exc_info.value.status == 404
    assert exc_info.value.code == "resource.not-found"


async def _seed_tree(session: AsyncSession) -> tuple[Department, Department]:
    root = Department(name="Root", path="/root/", depth=0)
    other = Department(name="Other", path="/other/", depth=0)
    session.add_all([root, other])
    await session.flush()
    return root, other


@pytest.mark.asyncio
async def test_apply_scope_dept_uses_scope_value_when_set(
    db_session: AsyncSession,
) -> None:
    """User's own dept=Root but assignment.scope_value=Other → sees Other rows."""
    root, other = await _seed_tree(db_session)
    user = User(
        email="u@test",
        password_hash="x",
        full_name="U",
        department_id=root.id,
    )
    db_session.add(user)
    role = Role(code="r6b2", name="R")
    db_session.add(role)
    await db_session.flush()
    perm = (
        await db_session.execute(select(Permission).where(Permission.code == "user:list"))
    ).scalar_one()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id, scope="dept"))
    db_session.add(UserRole(user_id=user.id, role_id=role.id, scope_value=other.id))
    await db_session.flush()

    # Scope map on User maps DEPT -> department_id field.
    perms = {"user:list": ScopeEnum.DEPT}
    stmt = select(User)
    scoped = apply_scope(stmt, user, "user:list", User, perms)
    compiled = str(scoped.compile(compile_kwargs={"literal_binds": True}))
    # The anchor should derive from UserRole.scope_value (=other.id),
    # not user.department_id (=root.id). Either the literal binds leak or
    # the SQL uses COALESCE parametrically.
    assert other.id.hex in compiled or str(other.id) in compiled or "coalesce" in compiled.lower()


@pytest.mark.asyncio
async def test_apply_scope_dept_falls_back_to_user_dept_when_scope_value_null(
    db_session: AsyncSession,
) -> None:
    """NULL scope_value → identical to Plan 4 behaviour."""
    root, _ = await _seed_tree(db_session)
    user = User(
        email="u2@test",
        password_hash="x",
        full_name="U2",
        department_id=root.id,
    )
    db_session.add(user)
    role = Role(code="r6b2b", name="R2")
    db_session.add(role)
    await db_session.flush()
    perm = (
        await db_session.execute(select(Permission).where(Permission.code == "user:list"))
    ).scalar_one()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id, scope="dept"))
    db_session.add(UserRole(user_id=user.id, role_id=role.id, scope_value=None))
    await db_session.flush()

    perms = {"user:list": ScopeEnum.DEPT}
    stmt = select(User)
    scoped = apply_scope(stmt, user, "user:list", User, perms)
    compiled = str(scoped.compile(compile_kwargs={"literal_binds": True}))
    # Fallback anchor is user.department_id (root). asyncpg renders UUID
    # literals without hyphens, so match against the hex form.
    assert root.id.hex in compiled or str(root.id) in compiled


@pytest.mark.asyncio
async def test_apply_scope_dept_tree_uses_scope_value_subtree(
    db_session: AsyncSession,
) -> None:
    """DEPT_TREE with scope_value=Other expands to Other's subtree, not Root's."""
    root, other = await _seed_tree(db_session)
    child_of_other = Department(
        name="OtherChild", parent_id=other.id, path="/other/child/", depth=1
    )
    db_session.add(child_of_other)
    await db_session.flush()

    user = User(
        email="u3@test",
        password_hash="x",
        full_name="U3",
        department_id=root.id,
    )
    db_session.add(user)
    role = Role(code="r6b4", name="R4")
    db_session.add(role)
    await db_session.flush()
    # user:list is already seeded by migration 0003; fetch instead of insert
    # (a fresh Permission row would violate permissions_code_key).
    perm = (
        await db_session.execute(select(Permission).where(Permission.code == "user:list"))
    ).scalar_one()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id, scope="dept_tree"))
    db_session.add(UserRole(user_id=user.id, role_id=role.id, scope_value=other.id))
    await db_session.flush()

    perms = {"user:list": ScopeEnum.DEPT_TREE}
    stmt = select(User)
    scoped = apply_scope(stmt, user, "user:list", User, perms)
    compiled = str(scoped.compile(compile_kwargs={"literal_binds": True}))
    # The SQL must use COALESCE(scope_value, user.department_id) as the anchor
    # so that the scope_value (other.id) drives subtree expansion, not the
    # user's own department.  scope_value is a DB column reference so it won't
    # be inlined; presence of `coalesce` and `scope_value` column name confirms
    # the correct branch is used.  Same assertion pattern as the DEPT test.
    assert "coalesce" in compiled.lower()
    assert "scope_value" in compiled
