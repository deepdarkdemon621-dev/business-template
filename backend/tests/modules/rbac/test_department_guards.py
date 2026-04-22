from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guards import GuardViolationError
from app.modules.auth.models import User
from app.modules.rbac.guards import HasAssignedUsers, HasChildren, NoCycle
from app.modules.rbac.models import Department

pytestmark = pytest.mark.asyncio


async def test_has_children_rejects_when_active_child_exists(
    db_session: AsyncSession,
) -> None:
    parent = Department(name="P", path="/p/", depth=0)
    db_session.add(parent)
    await db_session.flush()
    child = Department(name="C", parent_id=parent.id, path="/p/c/", depth=1)
    db_session.add(child)
    await db_session.flush()

    with pytest.raises(GuardViolationError) as ei:
        await HasChildren().check(db_session, parent)
    assert ei.value.code == "department.has-children"


async def test_has_children_passes_when_only_inactive_children(
    db_session: AsyncSession,
) -> None:
    parent = Department(name="P2", path="/p2/", depth=0)
    db_session.add(parent)
    await db_session.flush()
    child = Department(name="C2", parent_id=parent.id, path="/p2/c2/", depth=1, is_active=False)
    db_session.add(child)
    await db_session.flush()

    await HasChildren().check(db_session, parent)


async def test_has_assigned_users_rejects_when_active_user_assigned(
    db_session: AsyncSession,
) -> None:
    dept = Department(name="D", path="/d/", depth=0)
    db_session.add(dept)
    await db_session.flush()
    u = User(email="hu@test", password_hash="x", full_name="HU", department_id=dept.id)
    db_session.add(u)
    await db_session.flush()

    with pytest.raises(GuardViolationError) as ei:
        await HasAssignedUsers().check(db_session, dept)
    assert ei.value.code == "department.has-users"


async def test_no_cycle_rejects_self_parent(db_session: AsyncSession) -> None:
    d = Department(name="X", path="/x/", depth=0)
    db_session.add(d)
    await db_session.flush()

    with pytest.raises(GuardViolationError) as ei:
        await NoCycle().check(db_session, d, new_parent_id=d.id)
    assert ei.value.code == "department.self-parent"


async def test_no_cycle_rejects_move_into_descendant(
    db_session: AsyncSession,
) -> None:
    root = Department(name="R", path="/r/", depth=0)
    db_session.add(root)
    await db_session.flush()
    child = Department(name="C", parent_id=root.id, path="/r/c/", depth=1)
    db_session.add(child)
    await db_session.flush()

    with pytest.raises(GuardViolationError) as ei:
        await NoCycle().check(db_session, root, new_parent_id=child.id)
    assert ei.value.code == "department.cycle-detected"


async def test_no_cycle_passes_for_unrelated_parent(
    db_session: AsyncSession,
) -> None:
    a = Department(name="A", path="/a/", depth=0)
    b = Department(name="B", path="/b/", depth=0)
    db_session.add_all([a, b])
    await db_session.flush()

    await NoCycle().check(db_session, a, new_parent_id=b.id)
