from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest

from app.modules.audit.context import AuditContext, audit_context


@pytest.fixture
def audit_ctx() -> Generator[AuditContext, None, None]:
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


@pytest.fixture
def anon_audit_ctx() -> Generator[AuditContext, None, None]:
    ctx = AuditContext(actor_user_id=None, actor_ip="198.51.100.7", actor_user_agent="anon-ua")
    token = audit_context.set(ctx)
    try:
        yield ctx
    finally:
        audit_context.reset(token)
