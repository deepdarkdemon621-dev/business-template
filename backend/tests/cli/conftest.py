"""CLI-test-scoped fixtures.

The CLI tests use `CliRunner` to invoke `cli.app`, which internally calls
`asyncio.run(_run())`. Each `asyncio.run()` creates a fresh event loop, but
the module-level `engine` in `app.core.database` holds an asyncpg connection
pool bound to whichever loop first touched it. That pool must be disposed
between invocations or asyncpg raises "attached to a different loop".

This autouse fixture disposes the engine's pool after each CLI test so the
next one starts clean.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.database import engine


@pytest.fixture(autouse=True)
def _dispose_engine_pool_after_test():
    yield
    asyncio.run(engine.dispose())
