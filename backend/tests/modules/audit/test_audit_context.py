import pytest

from app.modules.audit.context import audit_context, get_context


def test_get_context_raises_when_unset():
    # Reset the var in this test scope
    token = audit_context.set(None)
    try:
        with pytest.raises(RuntimeError, match="audit_context is unset"):
            get_context()
    finally:
        audit_context.reset(token)


def test_get_context_returns_set_value(audit_ctx):
    ctx = get_context()
    assert ctx.actor_user_id == audit_ctx.actor_user_id
    assert ctx.actor_ip == "10.0.0.4"
    assert ctx.actor_user_agent == "pytest-agent"


def test_anon_context_has_null_actor(anon_audit_ctx):
    ctx = get_context()
    assert ctx.actor_user_id is None
    assert ctx.actor_ip == "198.51.100.7"
