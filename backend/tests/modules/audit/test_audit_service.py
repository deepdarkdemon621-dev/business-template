# backend/tests/modules/audit/test_audit_service.py
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.audit.service import audit


def _fake_user(**kw):
    defaults = dict(id=uuid.uuid4(), email="a@b.com", full_name="A B", is_active=True, department_id=None)
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _fake_role(**kw):
    defaults = dict(id=uuid.uuid4(), code="r1", name="R One", is_builtin=False, is_superadmin=False)
    defaults.update(kw)
    return SimpleNamespace(**defaults)


async def test_user_created_event_shape(db_session, db_audit_ctx):
    u = _fake_user()
    await audit.user_created(db_session, u)
    await db_session.flush()
    rows = (await db_session.execute(select(AuditEvent).where(AuditEvent.event_type == "user.created"))).scalars().all()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "create"
    assert ev.resource_type == "user"
    assert ev.resource_id == u.id
    assert ev.resource_label == u.email
    assert ev.actor_user_id == db_audit_ctx.actor_user_id
    assert str(ev.actor_ip) == "10.0.0.4"
    assert ev.after["email"] == "a@b.com"
    assert ev.before is None and ev.changes is None


async def test_user_updated_records_changes_only(db_session, db_audit_ctx):
    u = _fake_user()
    await audit.user_updated(db_session, u, {"full_name": ["Old", "New"]})
    await db_session.flush()
    ev = (await db_session.execute(select(AuditEvent).where(AuditEvent.event_type == "user.updated"))).scalar_one()
    assert ev.changes == {"full_name": ["Old", "New"]}
    assert ev.before is None and ev.after is None


async def test_role_permissions_updated_stores_added_removed(db_session, db_audit_ctx):
    r = _fake_role()
    added = [{"permission_code": "x:read", "scope": "global"}]
    removed = [{"permission_code": "y:read", "scope": "own"}]
    await audit.role_permissions_updated(db_session, r, added, removed)
    await db_session.flush()
    ev = (await db_session.execute(select(AuditEvent).where(AuditEvent.event_type == "role.permissions_updated"))).scalar_one()
    assert ev.metadata_["added"] == added
    assert ev.metadata_["removed"] == removed


async def test_login_failed_stores_reason_and_no_resource(db_session, anon_audit_ctx):
    await audit.login_failed(db_session, "x@y.com", "bad_password")
    await db_session.flush()
    ev = (await db_session.execute(select(AuditEvent).where(AuditEvent.event_type == "auth.login_failed"))).scalar_one()
    assert ev.actor_user_id is None
    assert str(ev.actor_ip) == "198.51.100.7"
    assert ev.resource_type is None
    assert ev.metadata_ == {"email": "x@y.com", "reason": "bad_password"}


async def test_snapshot_strips_sensitive_keys(db_session, db_audit_ctx):
    u = _fake_user()
    # forcibly pollute — simulates a service handing a dict with password_hash
    import app.modules.audit.service as svc
    ev = await svc.audit._record(
        db_session,
        event_type="user.created", action="create",
        resource_type="user", resource_id=u.id, resource_label=u.email,
        after={"email": u.email, "password_hash": "SECRET", "token": "SECRET2"},
    )
    await db_session.flush()
    assert "password_hash" not in ev.after
    assert "token" not in ev.after
    assert ev.after["email"] == u.email
