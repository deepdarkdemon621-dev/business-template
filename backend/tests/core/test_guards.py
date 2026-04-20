from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.guards import (
    GuardViolationError,
    NoDependents,
    ServiceBase,
    StateAllows,
)


@pytest.fixture
def session():
    s = AsyncMock()

    @asynccontextmanager
    async def _begin():
        yield

    s.begin = _begin
    return s


async def test_no_dependents_passes_when_count_zero(session):
    result = MagicMock()
    result.scalar_one.return_value = 0
    session.execute.return_value = result

    guard = NoDependents(relation="users", fk_col="department_id")
    await guard.check(session, SimpleNamespace(id=1))


async def test_no_dependents_raises_when_count_positive(session):
    result = MagicMock()
    result.scalar_one.return_value = 3
    session.execute.return_value = result

    guard = NoDependents(relation="users", fk_col="department_id")
    with pytest.raises(GuardViolationError) as ei:
        await guard.check(session, SimpleNamespace(id=1))
    assert ei.value.code == "has-dependents"
    assert ei.value.ctx == {"relation": "users", "fk_col": "department_id", "count": 3}


async def test_state_allows_passes(session):
    guard = StateAllows(field="status", allowed=["draft", "open"])
    await guard.check(session, SimpleNamespace(status="draft"))


async def test_state_allows_raises_with_ctx(session):
    guard = StateAllows(field="status", allowed=["draft", "open"])
    with pytest.raises(GuardViolationError) as ei:
        await guard.check(session, SimpleNamespace(status="closed"))
    assert ei.value.code == "state-not-allowed"
    assert ei.value.ctx == {"field": "status", "actual": "closed", "allowed": ["draft", "open"]}


async def test_service_base_runs_delete_guards(session):
    calls: list[str] = []

    class _Guard:
        async def check(self, s, i, *, actor=None):
            calls.append("checked")

    class _Model:
        __tablename__ = "t"
        __guards__ = {"delete": [_Guard(), _Guard()]}

    svc = ServiceBase()
    svc.model = _Model
    instance = SimpleNamespace(id=7)

    await svc.delete(session, instance)

    assert calls == ["checked", "checked"]
    session.delete.assert_awaited_once_with(instance)


async def test_service_base_aborts_on_guard_failure(session):
    class _Guard:
        async def check(self, s, i, *, actor=None):
            raise GuardViolationError(code="has-dependents", ctx={"relation": "x"})

    class _Model:
        __tablename__ = "t"
        __guards__ = {"delete": [_Guard()]}

    svc = ServiceBase()
    svc.model = _Model

    with pytest.raises(GuardViolationError):
        await svc.delete(session, SimpleNamespace(id=1))
    session.delete.assert_not_called()
