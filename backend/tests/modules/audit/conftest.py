from __future__ import annotations

import uuid

import pytest

from app.modules.audit.context import AuditContext, set_context_for_test


@pytest.fixture
def audit_ctx() -> AuditContext:
    ctx = AuditContext(
        actor_user_id=uuid.uuid4(),
        actor_ip="10.0.0.4",
        actor_user_agent="pytest-agent",
    )
    set_context_for_test(ctx)
    return ctx


@pytest.fixture
def anon_audit_ctx() -> AuditContext:
    ctx = AuditContext(actor_user_id=None, actor_ip="198.51.100.7", actor_user_agent="anon-ua")
    set_context_for_test(ctx)
    return ctx
