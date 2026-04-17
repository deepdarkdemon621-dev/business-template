"""conftest for auth endpoint integration tests.

Sets the asyncio fixture loop scope to 'module' so all tests in this module
share a single event loop. This prevents the module-level singletons (SQLAlchemy
engine pool, redis_pool) from becoming bound to a dead loop between tests.
"""

import pytest


# Tell pytest-asyncio to use one event loop for the entire module.
# This keeps the engine / redis connection pools alive across all tests.
@pytest.fixture(scope="module")
def event_loop_policy():
    """Use the default event loop policy (asyncio)."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()
