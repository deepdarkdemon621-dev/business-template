from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_scope_value_column_exists(db_session: AsyncSession) -> None:
    def _inspect(sync_conn):
        insp = inspect(sync_conn)
        cols = {c["name"]: c for c in insp.get_columns("user_roles")}
        assert "scope_value" in cols
        assert cols["scope_value"]["nullable"] is True

    await db_session.run_sync(lambda s: _inspect(s.connection()))


async def test_partial_index_on_scope_value(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'user_roles' AND indexname = 'ix_user_roles_scope_value'"
        )
    )
    row = result.first()
    assert row is not None
    assert "scope_value IS NOT NULL" in row[0]


async def test_action_check_allows_move(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
            "JOIN pg_class t ON t.oid = c.conrelid "
            "WHERE t.relname = 'permissions' AND c.conname = 'ck_permissions_action'"
        )
    )
    row = result.first()
    assert row is not None
    assert "'move'" in row[0]


async def test_department_permissions_seeded(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT code FROM permissions WHERE code LIKE 'department:%' ORDER BY code")
    )
    codes = [r[0] for r in result]
    assert "department:create" in codes
    assert "department:read" in codes
    assert "department:update" in codes
    assert "department:delete" in codes
    assert "department:move" in codes


async def test_admin_role_granted_dept_permissions(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT p.code, rp.scope "
            "FROM role_permissions rp "
            "JOIN permissions p ON p.id = rp.permission_id "
            "JOIN roles r ON r.id = rp.role_id "
            "WHERE r.code = 'admin' AND p.code LIKE 'department:%' "
            "ORDER BY p.code"
        )
    )
    rows = [(r[0], r[1]) for r in result]
    grants = dict(rows)
    assert grants.get("department:create") == "global"
    assert grants.get("department:read") == "global"
    assert grants.get("department:update") == "global"
    assert grants.get("department:delete") == "global"
    assert grants.get("department:move") == "global"
