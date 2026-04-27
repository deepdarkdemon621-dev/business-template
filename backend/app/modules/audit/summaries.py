"""Server-rendered one-liners for audit log entries.

Each event_type maps to a short human-readable summary used in the audit
log viewer. Server-rendered (not client-side) so future i18n is a
mechanical per-branch translation key swap, not a refactor.
"""
# backend/app/modules/audit/summaries.py
from __future__ import annotations

from typing import Any


def render_summary(event_type: str, action: str, resource_label: str | None, metadata: dict[str, Any] | None, changes: dict[str, Any] | None) -> str:
    """Human-readable one-liner for audit list display. Server-rendered for i18n-readiness."""
    rl = resource_label or ""
    md = metadata or {}
    ch = changes or {}
    match event_type:
        case "user.created":
            return f"Created user '{rl}'"
        case "user.updated":
            fields = ", ".join(ch.keys()) if ch else "no fields"
            return f"Updated user '{rl}' ({fields})"
        case "user.deleted":
            return f"Deleted user '{rl}'"
        case "role.created":
            return f"Created role '{rl}'"
        case "role.updated":
            fields = ", ".join(ch.keys()) if ch else "no fields"
            return f"Updated role '{rl}' ({fields})"
        case "role.deleted":
            return f"Deleted role '{rl}'"
        case "role.permissions_updated":
            added = len(md.get("added", []))
            removed = len(md.get("removed", []))
            return f"Updated permissions on role '{rl}' (+{added}/-{removed})"
        case "user.role_assigned":
            return f"Assigned role '{md.get('role_code', '')}' to user '{rl}'"
        case "user.role_revoked":
            return f"Revoked role '{md.get('role_code', '')}' from user '{rl}'"
        case "department.created":
            return f"Created department '{rl}'"
        case "department.updated":
            fields = ", ".join(ch.keys()) if ch else "no fields"
            return f"Updated department '{rl}' ({fields})"
        case "department.deleted":
            return f"Deleted department '{rl}'"
        case "auth.login_succeeded":
            return f"Login: {rl}"
        case "auth.login_failed":
            reason = md.get("reason", "unknown")
            email = md.get("email", "")
            return f"Failed login for '{email}' ({reason})"
        case "auth.logout":
            return f"Logout: {rl}"
        case "auth.password_changed":
            return f"Password changed: {rl}"
        case "auth.password_reset_requested":
            return f"Password reset requested: {rl}"
        case "auth.password_reset_consumed":
            return f"Password reset consumed: {rl}"
        case "auth.session_revoked":
            by_admin = md.get("by_admin", False)
            who = "admin" if by_admin else "user"
            return f"Session revoked by {who}: {rl}"
        case "audit.pruned":
            return f"Audit log pruned: {md.get('deleted_count', 0)} rows older than {md.get('cutoff', '')}"
        case _:
            return f"{event_type} on {rl}"
