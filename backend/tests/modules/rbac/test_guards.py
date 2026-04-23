from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.guards import GuardViolationError
from app.modules.auth.models import User
from app.modules.rbac.guards import LastOfKind
from app.modules.rbac.models import Role, UserRole

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def superadmin_role(db_session: AsyncSession) -> Role:
    role = Role(code="superadmin_test", name="Super", is_superadmin=True)
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def two_superadmins(db_session: AsyncSession, superadmin_role: Role) -> list[User]:
    users = []
    for email in ("sa1@ex.com", "sa2@ex.com"):
        u = User(email=email, password_hash=hash_password("pw-aaa111"), full_name=email)
        db_session.add(u)
        await db_session.flush()
        db_session.add(UserRole(user_id=u.id, role_id=superadmin_role.id))
        users.append(u)
    await db_session.flush()
    return users


async def test_passes_when_role_code_mismatch() -> None:
    session = AsyncMock()
    actor = SimpleNamespace(id=None, is_superadmin=False)
    target = SimpleNamespace(id=None)
    g = LastOfKind("superadmin")
    await g.check(session, target, actor=actor, role_code="member")


async def test_raises_when_removing_last_superadmin(
    db_session: AsyncSession, superadmin_role: Role
) -> None:
    u = User(email="only@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Only")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=superadmin_role.id))
    await db_session.flush()

    actor = SimpleNamespace(id=None, is_superadmin=False)
    g = LastOfKind("superadmin_test")
    with pytest.raises(GuardViolationError) as ei:
        await g.check(db_session, u, actor=actor, role_code="superadmin_test")
    assert ei.value.code == "last-of-kind"
    assert ei.value.ctx["role_code"] == "superadmin_test"
    assert ei.value.ctx["remaining"] == 1


async def test_passes_when_another_superadmin_remains(
    db_session: AsyncSession, two_superadmins: list[User]
) -> None:
    actor = SimpleNamespace(id=None, is_superadmin=False)
    g = LastOfKind("superadmin_test")
    await g.check(db_session, two_superadmins[0], actor=actor, role_code="superadmin_test")


async def test_superadmin_bypasses(db_session: AsyncSession, superadmin_role: Role) -> None:
    u = User(email="alone@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Alone")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=superadmin_role.id))
    await db_session.flush()

    actor = SimpleNamespace(id=None, is_superadmin=True)
    await LastOfKind("superadmin_test").check(
        db_session, u, actor=actor, role_code="superadmin_test"
    )


@pytest.mark.asyncio
async def test_superadmin_role_locked_refuses_mutation(db_session: AsyncSession) -> None:
    from app.core.guards import GuardViolationError
    from app.modules.rbac.guards import SuperadminRoleLocked
    from app.modules.rbac.models import Role
    from sqlalchemy import select

    role = (
        await db_session.execute(select(Role).where(Role.is_superadmin.is_(True)))
    ).scalar_one()

    with pytest.raises(GuardViolationError) as exc:
        await SuperadminRoleLocked().check(db_session, role)
    assert exc.value.code == "role.superadmin-locked"


@pytest.mark.asyncio
async def test_superadmin_role_locked_skips_non_superadmin(db_session: AsyncSession) -> None:
    from app.modules.rbac.guards import SuperadminRoleLocked
    from app.modules.rbac.models import Role
    from sqlalchemy import select

    admin = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()
    # Should not raise.
    await SuperadminRoleLocked().check(db_session, admin)


@pytest.mark.asyncio
async def test_builtin_role_locked_refuses_metadata_edit(db_session: AsyncSession) -> None:
    from app.core.guards import GuardViolationError
    from app.modules.rbac.guards import BuiltinRoleLocked
    from app.modules.rbac.models import Role
    from sqlalchemy import select

    admin = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()

    with pytest.raises(GuardViolationError) as exc:
        await BuiltinRoleLocked().check(
            db_session, admin, changing={"name"}
        )
    assert exc.value.code == "role.builtin-locked"


@pytest.mark.asyncio
async def test_builtin_role_locked_allows_matrix_only_edits(db_session: AsyncSession) -> None:
    from app.modules.rbac.guards import BuiltinRoleLocked
    from app.modules.rbac.models import Role
    from sqlalchemy import select

    admin = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()

    # Matrix-only edits pass (changing set contains only "permissions").
    await BuiltinRoleLocked().check(db_session, admin, changing={"permissions"})


@pytest.mark.asyncio
async def test_builtin_role_locked_refuses_delete(db_session: AsyncSession) -> None:
    from app.core.guards import GuardViolationError
    from app.modules.rbac.guards import BuiltinRoleLocked
    from app.modules.rbac.models import Role
    from sqlalchemy import select

    admin = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()

    with pytest.raises(GuardViolationError) as exc:
        # No `changing` kwarg means "delete" in the guard's contract.
        await BuiltinRoleLocked().check(db_session, admin)
    assert exc.value.code == "role.builtin-locked"
