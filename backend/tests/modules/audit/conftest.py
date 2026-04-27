from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.context import AuditContext, audit_context
from app.modules.auth.models import User


@pytest.fixture
def audit_ctx() -> Generator[AuditContext, None, None]:
    """Sync audit context with a random actor_user_id.

    NOTE: Only use this fixture in tests that do NOT write to the DB (e.g.
    purely in-memory / sync tests). For async DB tests that insert AuditEvent
    rows, use `db_audit_ctx` instead — it creates a real User row to satisfy
    the audit_events.actor_user_id FK constraint.
    """
    ctx = AuditContext(
        actor_user_id=uuid.uuid4(),
        actor_ip="10.0.0.4",
        actor_user_agent="pytest-agent",
    )
    token = audit_context.set(ctx)
    try:
        yield ctx
    finally:
        audit_context.reset(token)


@pytest_asyncio.fixture
async def db_audit_ctx(db_session: AsyncSession) -> AsyncGenerator[AuditContext, None]:
    """Async audit context that inserts a real User into the test DB.

    Use this in async tests that write AuditEvent rows so the FK
    audit_events.actor_user_id → users.id is satisfied.
    """
    actor_id = uuid.uuid4()
    user = User(
        id=actor_id,
        email=f"audit-actor-{actor_id}@test.invalid",
        password_hash="x",
        full_name="Audit Actor",
    )
    db_session.add(user)
    await db_session.flush()
    ctx = AuditContext(actor_user_id=actor_id, actor_ip="10.0.0.4", actor_user_agent="pytest-agent")
    token = audit_context.set(ctx)
    try:
        yield ctx
    finally:
        audit_context.reset(token)


@pytest.fixture
def anon_audit_ctx() -> Generator[AuditContext, None, None]:
    ctx = AuditContext(actor_user_id=None, actor_ip="198.51.100.7", actor_user_agent="anon-ua")
    token = audit_context.set(ctx)
    try:
        yield ctx
    finally:
        audit_context.reset(token)
