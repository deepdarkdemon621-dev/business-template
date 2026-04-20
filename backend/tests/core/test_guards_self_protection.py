from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guards import GuardViolationError, SelfProtection

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session_stub(db_session: AsyncSession) -> AsyncSession:
    return db_session


async def test_raises_when_actor_equals_target(session_stub: AsyncSession) -> None:
    uid = uuid.uuid4()
    target = SimpleNamespace(id=uid)
    actor = SimpleNamespace(id=uid, is_superadmin=False)
    g = SelfProtection()
    with pytest.raises(GuardViolationError) as ei:
        await g.check(session_stub, target, actor=actor)
    assert ei.value.code == "self-protection"


async def test_passes_when_actor_different(session_stub: AsyncSession) -> None:
    target = SimpleNamespace(id=uuid.uuid4())
    actor = SimpleNamespace(id=uuid.uuid4(), is_superadmin=False)
    await SelfProtection().check(session_stub, target, actor=actor)


async def test_superadmin_bypasses(session_stub: AsyncSession) -> None:
    uid = uuid.uuid4()
    target = SimpleNamespace(id=uid)
    actor = SimpleNamespace(id=uid, is_superadmin=True)
    await SelfProtection().check(session_stub, target, actor=actor)
