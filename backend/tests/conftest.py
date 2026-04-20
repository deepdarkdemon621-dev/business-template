import os
import re
import subprocess

# Force the test DB before any app imports. conftest refuses to run if
# DATABASE_URL_TEST is unset or doesn't end in *_test (accident guard).
_test_db = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql+asyncpg://postgres:postgres@db:5432/business_template_test",
)
if not _test_db.rstrip("/").endswith("_test"):
    raise RuntimeError(
        f"Refusing to run tests against non-test DB: {_test_db}. "
        "DATABASE_URL_TEST must end in '_test' to prevent accidents."
    )
os.environ["DATABASE_URL"] = _test_db

# Settings builds its DSN from discrete POSTGRES_* env vars (no DATABASE_URL
# support), so parse the test URL and override POSTGRES_DB to match. This
# ensures `app.core.database.engine` connects to the *_test DB on import.
_dsn_re = re.compile(
    r"^postgresql(?:\+asyncpg)?://(?P<user>[^:]+):(?P<pw>[^@]+)@(?P<host>[^:/]+):(?P<port>\d+)/(?P<db>[^/?]+)"
)
_m = _dsn_re.match(_test_db)
if _m is None:
    raise RuntimeError(f"Could not parse DATABASE_URL_TEST: {_test_db}")
os.environ["POSTGRES_USER"] = _m.group("user")
os.environ["POSTGRES_PASSWORD"] = _m.group("pw")
os.environ["POSTGRES_HOST"] = _m.group("host")
os.environ["POSTGRES_PORT"] = _m.group("port")
os.environ["POSTGRES_DB"] = _m.group("db")

os.environ.setdefault("SECRET_KEY", "x" * 40)
os.environ.setdefault("APP_ENV", "test")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import engine, get_session  # noqa: E402
from app.main import app as _app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_test_db():
    """Run alembic downgrade base + upgrade head once per session against test DB.

    Uses a subprocess so alembic's own `asyncio.run()` doesn't conflict with
    pytest-asyncio's running event loop.
    """
    env = {**os.environ}
    subprocess.run(
        ["uv", "run", "alembic", "downgrade", "base"],
        check=True,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        check=True,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    yield


@pytest_asyncio.fixture
async def db_session():
    """Per-test transactional session; rolls back at teardown."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture
async def client_with_db(db_session: AsyncSession):
    """TestClient with get_session overridden to yield the per-test rollback session."""

    async def _override():
        yield db_session

    _app.dependency_overrides[get_session] = _override
    client = TestClient(_app)
    try:
        yield client
    finally:
        _app.dependency_overrides.clear()
