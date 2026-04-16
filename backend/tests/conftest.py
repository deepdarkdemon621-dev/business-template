import os

# Ensure tests use a predictable SECRET_KEY (min 32 chars required by Settings)
os.environ.setdefault("SECRET_KEY", "x" * 40)
os.environ.setdefault("APP_ENV", "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app as _app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app)
