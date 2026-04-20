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
    """Reset + migrate the test DB once per session.

    Drops the `public` schema and runs `alembic upgrade head` in a subprocess
    (alembic's own `asyncio.run()` conflicts with pytest-asyncio's running
    event loop, so we can't call it in-process). Schema drop is used instead
    of `alembic downgrade base` because the latter fails if prior runs left
    the DB half-migrated (e.g. tables dropped but alembic_version still at
    head).
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    reset_engine = create_async_engine(_test_db, isolation_level="AUTOCOMMIT")
    async with reset_engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    await reset_engine.dispose()

    env = {**os.environ}
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
    """AsyncClient (ASGI transport) with `get_session` overridden to yield the
    per-test rollback session.

    Uses httpx.AsyncClient + ASGITransport (not FastAPI's sync TestClient) so
    that request handling stays in the same event loop as the `db_session`
    fixture; otherwise asyncpg connections raise "Event loop is closed" when
    dispatched via TestClient's thread-bridge.
    """
    from httpx import ASGITransport, AsyncClient

    async def _override():
        yield db_session

    _app.dependency_overrides[get_session] = _override
    async with AsyncClient(
        transport=ASGITransport(app=_app), base_url="http://test"
    ) as client:
        try:
            yield client
        finally:
            _app.dependency_overrides.clear()
