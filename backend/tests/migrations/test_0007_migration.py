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


async def test_downgrade_reverses_migration() -> None:
    """Verify downgrade correctly reverses the 0007 migration.

    Does NOT use the `db_session` fixture — that fixture holds an open
    transaction, which would block the DDL inside the subprocess alembic run
    (ACCESS EXCLUSIVE lock wait).
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
                    # (a) audit_events table must NOT exist
                    result = sync_conn.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_name = 'audit_events'"
                        )
                    )
                    assert result.scalar_one_or_none() is None, (
                        "audit_events table should not exist after downgrade"
                    )

                    # (b) users.last_login_at column must NOT exist
                    result = sync_conn.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name = 'users' AND column_name = 'last_login_at'"
                        )
                    )
                    assert result.scalar_one_or_none() is None, (
                        "users.last_login_at should not exist after downgrade"
                    )

                    # (c) audit:list and audit:read must NOT exist
                    result = sync_conn.execute(
                        text(
                            "SELECT code FROM permissions "
                            "WHERE code IN ('audit:list', 'audit:read') "
                            "ORDER BY code"
                        )
                    )
                    codes = [r[0] for r in result]
                    assert len(codes) == 0, (
                        f"audit:list/audit:read should not exist after downgrade, got {codes}"
                    )

                    # (d) No orphaned role_permissions rows
                    result = sync_conn.execute(
                        text(
                            "SELECT rp.permission_id FROM role_permissions rp "
                            "WHERE rp.permission_id NOT IN (SELECT id FROM permissions)"
                        )
                    )
                    orphaned = result.fetchall()
                    assert len(orphaned) == 0, (
                        f"Found {len(orphaned)} orphaned role_permissions rows"
                    )

                    # (e) Sanity: role:list (from 0003) still exists — proves we
                    #     didn't accidentally nuke unrelated permissions data.
                    result = sync_conn.execute(
                        text(
                            "SELECT code FROM permissions "
                            "WHERE code = 'role:list'"
                        )
                    )
                    assert result.scalar_one_or_none() == "role:list", (
                        "role:list (from 0003) should still exist after downgrading 0007"
                    )

                await conn.run_sync(_check)
        finally:
            await async_engine.dispose()

    try:
        # Downgrade to 0006
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
