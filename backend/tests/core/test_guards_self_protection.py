from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.guards import GuardViolationError, SelfProtection

pytestmark = pytest.mark.asyncio


async def test_raises_when_actor_equals_target() -> None:
    session = AsyncMock()
    uid = uuid.uuid4()
    target = SimpleNamespace(id=uid)
    actor = SimpleNamespace(id=uid, is_superadmin=False)
    g = SelfProtection()
    with pytest.raises(GuardViolationError) as ei:
        await g.check(session, target, actor=actor)
    assert ei.value.code == "self-protection"


async def test_passes_when_actor_different() -> None:
    session = AsyncMock()
    target = SimpleNamespace(id=uuid.uuid4())
    actor = SimpleNamespace(id=uuid.uuid4(), is_superadmin=False)
    await SelfProtection().check(session, target, actor=actor)


async def test_superadmin_bypasses() -> None:
    session = AsyncMock()
    uid = uuid.uuid4()
    target = SimpleNamespace(id=uid)
    actor = SimpleNamespace(id=uid, is_superadmin=True)
    await SelfProtection().check(session, target, actor=actor)
