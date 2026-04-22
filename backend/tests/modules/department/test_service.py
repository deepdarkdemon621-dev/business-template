from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guards import GuardViolationError
from app.modules.department.service import DepartmentService
from app.modules.rbac.models import Department

pytestmark = pytest.mark.asyncio


async def _mk_tree(
    session: AsyncSession,
) -> tuple[Department, Department, Department, Department]:
    """Build:
    /a/
    /a/a1/
    /a/a1/a11/
    /b/
    """
    a = Department(name="a", path="/a/", depth=0)
    b = Department(name="b", path="/b/", depth=0)
    session.add_all([a, b])
    await session.flush()
    a1 = Department(name="a1", parent_id=a.id, path="/a/a1/", depth=1)
    session.add(a1)
    await session.flush()
    a11 = Department(name="a11", parent_id=a1.id, path="/a/a1/a11/", depth=2)
    session.add(a11)
    await session.flush()
    return a, b, a1, a11


async def test_move_leaf_under_new_parent_rewrites_path_and_depth(
    db_session: AsyncSession,
) -> None:
    _a, b, _a1, a11 = await _mk_tree(db_session)
    svc = DepartmentService()
    await svc.move_department(db_session, a11, new_parent_id=b.id)
    await db_session.flush()
    await db_session.refresh(a11)
    assert a11.parent_id == b.id
    assert a11.path.startswith("/b/")
    assert a11.depth == 1


async def test_move_subtree_rewrites_every_descendant(
    db_session: AsyncSession,
) -> None:
    _a, b, a1, a11 = await _mk_tree(db_session)
    svc = DepartmentService()
    await svc.move_department(db_session, a1, new_parent_id=b.id)
    await db_session.flush()
    await db_session.refresh(a1)
    await db_session.refresh(a11)
    assert a1.path.startswith("/b/")
    assert a1.depth == 1
    assert a11.path.startswith("/b/")
    assert a11.depth == 2
    assert a11.parent_id == a1.id  # parent link within subtree preserved


async def test_move_into_own_descendant_raises_cycle(
    db_session: AsyncSession,
) -> None:
    a, _b, _a1, a11 = await _mk_tree(db_session)
    svc = DepartmentService()
    with pytest.raises(GuardViolationError) as ei:
        await svc.move_department(db_session, a, new_parent_id=a11.id)
    assert ei.value.code == "department.cycle-detected"


async def test_move_to_same_parent_is_noop(db_session: AsyncSession) -> None:
    a, _b, a1, _a11 = await _mk_tree(db_session)
    svc = DepartmentService()
    await svc.move_department(db_session, a1, new_parent_id=a.id)
    await db_session.flush()
    await db_session.refresh(a1)
    assert a1.path == "/a/a1/"
    assert a1.depth == 1
