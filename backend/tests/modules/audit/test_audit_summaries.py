# backend/tests/modules/audit/test_audit_summaries.py
from app.modules.audit.summaries import render_summary


def test_user_created():
    assert render_summary("user.created", "create", "alice@example.com", None, None) == "Created user 'alice@example.com'"


def test_user_updated_lists_changed_fields():
    out = render_summary("user.updated", "update", "alice@example.com", None, {"name": ["A", "B"], "is_active": [True, False]})
    assert "alice@example.com" in out
    assert "name" in out and "is_active" in out


def test_role_permissions_updated_shows_counts():
    md = {
        "added": [{"permission_code": "a", "scope": "global"}],
        "removed": [{"permission_code": "b", "scope": "own"}, {"permission_code": "c", "scope": "dept"}],
        "scope_changed": [],
    }
    out = render_summary("role.permissions_updated", "update", "auditor", md, None)
    assert "+1" in out and "-2" in out


def test_role_permissions_updated_shows_scope_changed():
    md = {
        "added": [],
        "removed": [],
        "scope_changed": [{"permission_code": "user:read", "from_scope": "global", "to_scope": "dept_tree"}],
    }
    out = render_summary("role.permissions_updated", "update", "auditor", md, None)
    assert "~1" in out


def test_login_failed_shows_reason_and_email():
    out = render_summary("auth.login_failed", "login_failed", None, {"reason": "bad_password", "email": "x@y.com"}, None)
    assert "x@y.com" in out and "bad_password" in out


def test_session_revoked_by_admin_vs_self():
    admin_out = render_summary("auth.session_revoked", "session_revoked", "alice@x", {"by_admin": True}, None)
    self_out = render_summary("auth.session_revoked", "session_revoked", "alice@x", {"by_admin": False}, None)
    assert "admin" in admin_out and "user" in self_out


def test_pruned():
    out = render_summary("audit.pruned", "pruned", None, {"deleted_count": 5000, "cutoff": "2025-04-24"}, None)
    assert "5000" in out and "2025-04-24" in out


def test_unknown_event_type_has_fallback():
    out = render_summary("weird.thing", "update", "label", None, None)
    assert "weird.thing" in out
