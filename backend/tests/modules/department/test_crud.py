from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemDetails
from app.modules.department.crud import (
    build_list_flat_stmt,
    create_department,
    get_tree_rooted_at,
    soft_delete_department,
    update_department,
)
from app.modules.department.schemas import DepartmentCreateIn, DepartmentUpdateIn
from app.modules.rbac.models import Department

pytestmark = pytest.mark.asyncio


async def test_create_under_existing_parent_builds_path(
    db_session: AsyncSession, db_audit_ctx
) -> None:
    parent = Department(name="Root", path="/root/", depth=0)
    db_session.add(parent)
    await db_session.flush()

    created = await create_department(
        db_session, DepartmentCreateIn(name="Ops", parent_id=parent.id)
    )
    assert created.parent_id == parent.id
    assert created.depth == 1
    assert created.path.startswith("/root/")
    assert created.path.endswith("/")


async def test_create_with_unknown_parent_raises(db_session: AsyncSession, db_audit_ctx) -> None:
    with pytest.raises(ProblemDetails) as ei:
        await create_department(
            db_session,
            DepartmentCreateIn(name="X", parent_id=uuid.uuid4()),
        )
    assert ei.value.code == "resource.not-found"


async def test_update_renames(db_session: AsyncSession, db_audit_ctx) -> None:
    d = Department(name="Old", path="/old/", depth=0)
    db_session.add(d)
    await db_session.flush()

    updated = await update_department(db_session, d, DepartmentUpdateIn(name="New"))
    assert updated.name == "New"


async def test_soft_delete_toggles_is_active(db_session: AsyncSession, db_audit_ctx) -> None:
    d = Department(name="D", path="/d/", depth=0)
    db_session.add(d)
    await db_session.flush()

    await soft_delete_department(db_session, d, actor=None)
    assert d.is_active is False


async def test_tree_rooted_at_returns_self_plus_descendants(
    db_session: AsyncSession,
) -> None:
    root = Department(name="R", path="/r/", depth=0)
    db_session.add(root)
    await db_session.flush()
    child = Department(name="C", parent_id=root.id, path="/r/c/", depth=1)
    db_session.add(child)
    await db_session.flush()

    rows = await get_tree_rooted_at(db_session, root_id=root.id, include_inactive=True)
    names = {r.name for r in rows}
    assert names == {"R", "C"}


async def test_list_flat_stmt_filters_inactive_by_default() -> None:
    stmt = build_list_flat_stmt(is_active=True)
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "is_active" in compiled
