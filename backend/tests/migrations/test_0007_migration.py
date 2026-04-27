from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# pytest-asyncio runs in Mode.AUTO (see pyproject), so async defs here are
# auto-marked. A sync test in this module (downgrade) must stay sync to
# avoid deadlocking on db_session's open transaction.


async def test_audit_events_table_exists(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'audit_events'"
        )
    )
    assert result.scalar_one_or_none() == "audit_events"


async def test_audit_events_indexes(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'audit_events' ORDER BY indexname"
        )
    )
    names = [row[0] for row in result]
    for expected in (
        "ix_audit_events_action",
        "ix_audit_events_actor",
        "ix_audit_events_occurred_at_desc",
        "ix_audit_events_resource",
    ):
        assert expected in names, f"missing index {expected}; got {names}"


async def test_users_last_login_at_column(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'last_login_at'"
        )
    )
    assert result.scalar_one_or_none() == "last_login_at"


async def test_audit_perms_seeded_on_superadmin(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT p.code FROM permissions p "
            "JOIN role_permissions rp ON rp.permission_id = p.id "
            "JOIN roles r ON r.id = rp.role_id "
            "WHERE r.code = 'superadmin' AND p.code IN ('audit:list', 'audit:read') "
            "ORDER BY p.code"
        )
    )
    codes = [row[0] for row in result]
    assert codes == ["audit:list", "audit:read"]
