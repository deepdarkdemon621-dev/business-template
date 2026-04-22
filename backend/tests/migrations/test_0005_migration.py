from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

# pytest-asyncio runs in Mode.AUTO (see pyproject), so async defs here are
# auto-marked. A sync test in this module (downgrade) must stay sync to
# avoid deadlocking on db_session's open transaction.


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


async def test_downgrade_reverses_migration() -> None:
    """Verify downgrade correctly reverses the 0005 migration.

    Does NOT use the `db_session` fixture — that fixture holds an open
    transaction, which would block the `ALTER TABLE ... DROP CONSTRAINT`
    DDL inside the subprocess alembic run (ACCESS EXCLUSIVE lock wait).
    Instead, we open a fresh async engine *only* after each subprocess
    finishes, and dispose it before launching the next subprocess, so no
    lock conflict is possible.
    """
    import contextlib
    import os
    import subprocess

    from sqlalchemy.ext.asyncio import create_async_engine

    def run(args):
        subprocess.run(
            ["uv", "run", "alembic"] + args,
            check=True,
            env={**os.environ},
            cwd="/app",
        )

    async def _inspect_downgrade_state() -> None:
        user = os.environ["POSTGRES_USER"]
        pw = os.environ["POSTGRES_PASSWORD"]
        host = os.environ["POSTGRES_HOST"]
        port = os.environ["POSTGRES_PORT"]
        db = os.environ["POSTGRES_DB"]
        async_dsn = f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}"
        async_engine = create_async_engine(async_dsn, future=True)
        try:
            async with async_engine.connect() as conn:

                def _check(sync_conn):
                    insp = inspect(sync_conn)

                    # 1. scope_value column must NOT exist
                    cols = {c["name"]: c for c in insp.get_columns("user_roles")}
                    assert "scope_value" not in cols, (
                        "scope_value column should not exist after downgrade"
                    )

                    # 2. department:move permission must NOT exist
                    result = sync_conn.execute(
                        text("SELECT code FROM permissions WHERE code = 'department:move'")
                    )
                    assert result.first() is None, (
                        "department:move permission should not exist after downgrade"
                    )

                    # 3. Other 4 department perms (from 0003) must STILL exist
                    result = sync_conn.execute(
                        text(
                            "SELECT code FROM permissions "
                            "WHERE code IN ('department:create', 'department:read', "
                            "'department:update', 'department:delete') "
                            "ORDER BY code"
                        )
                    )
                    codes = [r[0] for r in result]
                    assert len(codes) == 4, f"Expected 4 department perms from 0003, got {codes}"
                    assert "department:create" in codes
                    assert "department:read" in codes
                    assert "department:update" in codes
                    assert "department:delete" in codes

                    # 4. ACTION CHECK should NOT contain 'move'
                    result = sync_conn.execute(
                        text(
                            "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                            "JOIN pg_class t ON t.oid = c.conrelid "
                            "WHERE t.relname = 'permissions' AND c.conname = 'ck_permissions_action'"
                        )
                    )
                    row = result.first()
                    assert row is not None
                    assert "'move'" not in row[0], (
                        "ck_permissions_action should not contain 'move' after downgrade"
                    )

                await conn.run_sync(_check)
        finally:
            await async_engine.dispose()

    try:
        # Downgrade to 0004
        run(["downgrade", "-1"])
        # Inspect via a dedicated async engine, then dispose it before
        # re-upgrading so the subprocess has a lock-free DB.
        await _inspect_downgrade_state()
        # Re-upgrade to head for consistency
        run(["upgrade", "head"])

    except subprocess.CalledProcessError:
        # Restore to head before propagating so later tests don't see partial state
        with contextlib.suppress(subprocess.CalledProcessError):
            run(["upgrade", "head"])
        raise
