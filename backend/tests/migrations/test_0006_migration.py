from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# pytest-asyncio runs in Mode.AUTO (see pyproject), so async defs here are
# auto-marked. A sync test in this module (downgrade) must stay sync to
# avoid deadlocking on db_session's open transaction.


async def test_role_create_permission_exists(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT code, resource FROM permissions WHERE code = 'role:create'")
    )
    row = result.first()
    assert row is not None
    assert row[0] == "role:create"
    assert row[1] == "role"


async def test_role_update_permission_exists(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT code, resource FROM permissions WHERE code = 'role:update'")
    )
    row = result.first()
    assert row is not None
    assert row[0] == "role:update"
    assert row[1] == "role"


async def test_role_delete_permission_exists(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT code, resource FROM permissions WHERE code = 'role:delete'")
    )
    row = result.first()
    assert row is not None
    assert row[0] == "role:delete"
    assert row[1] == "role"


async def test_admin_role_granted_role_crud_permissions(
    db_session: AsyncSession,
) -> None:
    result = await db_session.execute(
        text(
            "SELECT p.code, rp.scope "
            "FROM role_permissions rp "
            "JOIN permissions p ON p.id = rp.permission_id "
            "JOIN roles r ON r.id = rp.role_id "
            "WHERE r.code = 'admin' AND p.code LIKE 'role:%' "
            "ORDER BY p.code"
        )
    )
    rows = [(r[0], r[1]) for r in result]
    grants = dict(rows)
    assert grants.get("role:create") == "global"
    assert grants.get("role:update") == "global"
    assert grants.get("role:delete") == "global"


async def test_admin_role_retains_prior_role_permissions(
    db_session: AsyncSession,
) -> None:
    """Verify role:list and role:read (from 0003) are still granted to admin."""
    result = await db_session.execute(
        text(
            "SELECT p.code, rp.scope "
            "FROM role_permissions rp "
            "JOIN permissions p ON p.id = rp.permission_id "
            "JOIN roles r ON r.id = rp.role_id "
            "WHERE r.code = 'admin' AND p.code IN ('role:list', 'role:read', 'role:assign') "
            "ORDER BY p.code"
        )
    )
    rows = [(r[0], r[1]) for r in result]
    grants = dict(rows)
    assert grants.get("role:list") == "global"
    assert grants.get("role:read") == "global"
    assert grants.get("role:assign") == "global"


async def test_downgrade_reverses_migration() -> None:
    """Verify downgrade correctly reverses the 0006 migration.

    Does NOT use the `db_session` fixture — that fixture holds an open
    transaction, which would block the `DELETE FROM permissions ...`
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
                    # 1. role:create, role:update, role:delete must NOT exist
                    result = sync_conn.execute(
                        text(
                            "SELECT code FROM permissions "
                            "WHERE code IN ('role:create', 'role:update', 'role:delete') "
                            "ORDER BY code"
                        )
                    )
                    codes = [r[0] for r in result]
                    assert len(codes) == 0, (
                        f"role:create/update/delete should not exist after downgrade, got {codes}"
                    )

                    # 2. role:list, role:read, role:assign (from 0003) must STILL exist
                    result = sync_conn.execute(
                        text(
                            "SELECT code FROM permissions "
                            "WHERE code IN ('role:list', 'role:read', 'role:assign') "
                            "ORDER BY code"
                        )
                    )
                    codes = [r[0] for r in result]
                    assert len(codes) == 3, f"Expected 3 role perms from 0003, got {codes}"
                    assert "role:list" in codes
                    assert "role:read" in codes
                    assert "role:assign" in codes

                    # 3. No orphaned role_permissions rows for the deleted permissions
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

                await conn.run_sync(_check)
        finally:
            await async_engine.dispose()

    # Always restore to head, regardless of how this test exits
    # (assertion failure, subprocess error, etc.). Otherwise the DB stays
    # downgraded and cascades into later migration tests.
    #
    # Use the absolute revision target (NOT `-1`) so this test continues to
    # downgrade the *0006* boundary even after newer revisions land on top.
    try:
        run(["downgrade", "0005_plan6_dept_scope_value"])
        await _inspect_downgrade_state()
    finally:
        with contextlib.suppress(subprocess.CalledProcessError):
            run(["upgrade", "head"])
