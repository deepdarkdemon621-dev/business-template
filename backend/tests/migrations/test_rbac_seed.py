import contextlib
import os
import subprocess


def test_migration_round_trip_0003():
    """Round-trip the plan4 RBAC migration.

    The session-scoped `_prepare_test_db` fixture has already run
    `alembic upgrade head` at session start. This test downgrades to
    0002 and re-upgrades to head to verify the migration is reversible.
    On any failure we best-effort restore to head so later tests don't
    see a partial state.

    Uses a subprocess because `alembic/env.py` calls `asyncio.run()`
    which conflicts with pytest-asyncio's running event loop.
    """

    def run(args):
        subprocess.run(
            ["uv", "run", "alembic"] + args,
            check=True,
            env={**os.environ},
            cwd="/app",
        )

    try:
        run(["downgrade", "-1"])
        run(["upgrade", "head"])
    except subprocess.CalledProcessError:
        # Restore to head before propagating, so later tests don't see partial state.
        with contextlib.suppress(subprocess.CalledProcessError):
            run(["upgrade", "head"])
        raise
