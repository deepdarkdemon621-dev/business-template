from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit import crud
from app.modules.audit.context import get_context
from app.modules.audit.models import AuditEvent

# Substring fragments. Matched case-insensitively against any dict key in
# audit payloads. Note the breadth: `token` will also strip a hypothetical
# `token_count` field; `password` will strip `last_password_change_at`. Audit
# data is a one-way write — silent loss is preferable to leaking credentials,
# but if a future analytics field collides, rename it or scope this list.
_SENSITIVE_KEY_FRAGMENTS = ("password", "token", "secret", "api_key")


def _is_sensitive_key(key: str) -> bool:
    low = key.lower()
    return any(frag in low for frag in _SENSITIVE_KEY_FRAGMENTS)


def _strip_sensitive(value: Any) -> Any:
    """Strip credential-bearing keys from audit payloads.

    Recursively walks dicts and lists-of-dicts, dropping any key whose name
    contains a sensitive fragment. Audit rows persist forever; a leaked
    password_hash or refresh_token in `before`/`after`/`changes` JSONB would
    be a permanent credential exposure.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: _strip_sensitive(v) for k, v in value.items() if not _is_sensitive_key(k)}
    if isinstance(value, list):
        return [_strip_sensitive(item) for item in value]
    return value


def _diff_dict(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    """Diff two snapshots into the shape stored in `audit_events.changes`.

    Returns {field: [old, new]} for keys whose values differ. Keys present
    on only one side are reported with `None` on the missing side.
    """
    keys = set(before) | set(after)
    out: dict[str, list[Any]] = {}
    for k in keys:
        b = before.get(k)
        a = after.get(k)
        if b != a:
            out[k] = [b, a]
    return out


def _now() -> datetime:
    return datetime.now(UTC)


class AuditService:
    """All methods add AuditEvent rows to the passed session. Never commit."""

    # --- internal -----------------------------------------------------

    async def _record(
        self,
        session: AsyncSession,
        *,
        event_type: str,
        action: str,
        resource_type: str | None,
        resource_id: uuid.UUID | None,
        resource_label: str | None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        ctx = get_context()
        return await crud.create_event(
            session,
            occurred_at=_now(),
            event_type=event_type,
            action=action,
            actor_user_id=ctx.actor_user_id,
            actor_ip=ctx.actor_ip,
            actor_user_agent=ctx.actor_user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_label=resource_label,
            before=_strip_sensitive(before),
            after=_strip_sensitive(after),
            changes=_strip_sensitive(changes),
            metadata_=_strip_sensitive(metadata),
        )

    # --- User mutations ----------------------------------------------

    async def user_created(self, session: AsyncSession, user: Any) -> AuditEvent:
        return await self._record(
            session,
            event_type="user.created", action="create",
            resource_type="user", resource_id=user.id, resource_label=user.email,
            after=_user_snapshot(user),
        )

    async def user_updated(self, session: AsyncSession, user: Any, changes: dict[str, list[Any]]) -> AuditEvent:
        return await self._record(
            session,
            event_type="user.updated", action="update",
            resource_type="user", resource_id=user.id, resource_label=user.email,
            changes=changes,
        )

    async def user_deleted(self, session: AsyncSession, user_snapshot: dict[str, Any], user_id: uuid.UUID, email: str) -> AuditEvent:
        return await self._record(
            session,
            event_type="user.deleted", action="delete",
            resource_type="user", resource_id=user_id, resource_label=email,
            before=user_snapshot,
        )

    # --- Role mutations ----------------------------------------------

    async def role_created(self, session: AsyncSession, role: Any) -> AuditEvent:
        return await self._record(
            session,
            event_type="role.created", action="create",
            resource_type="role", resource_id=role.id, resource_label=role.code,
            after=_role_snapshot(role),
        )

    async def role_updated(self, session: AsyncSession, role: Any, changes: dict[str, list[Any]]) -> AuditEvent:
        return await self._record(
            session,
            event_type="role.updated", action="update",
            resource_type="role", resource_id=role.id, resource_label=role.code,
            changes=changes,
        )

    async def role_deleted(self, session: AsyncSession, role_snapshot: dict[str, Any], role_id: uuid.UUID, code: str) -> AuditEvent:
        return await self._record(
            session,
            event_type="role.deleted", action="delete",
            resource_type="role", resource_id=role_id, resource_label=code,
            before=role_snapshot,
        )

    async def role_permissions_updated(
        self, session: AsyncSession, role: Any, added: list[dict[str, str]], removed: list[dict[str, str]]
    ) -> AuditEvent:
        return await self._record(
            session,
            event_type="role.permissions_updated", action="update",
            resource_type="role", resource_id=role.id, resource_label=role.code,
            metadata={"added": added, "removed": removed},
        )

    async def user_role_assigned(
        self, session: AsyncSession, user: Any, role_code: str, scope: str, scope_value: str | None = None,
    ) -> AuditEvent:
        return await self._record(
            session,
            event_type="user.role_assigned", action="update",
            resource_type="user", resource_id=user.id, resource_label=user.email,
            metadata={"role_code": role_code, "scope": scope, "scope_value": scope_value},
        )

    async def user_role_revoked(
        self, session: AsyncSession, user: Any, role_code: str, scope: str, scope_value: str | None = None,
    ) -> AuditEvent:
        return await self._record(
            session,
            event_type="user.role_revoked", action="update",
            resource_type="user", resource_id=user.id, resource_label=user.email,
            metadata={"role_code": role_code, "scope": scope, "scope_value": scope_value},
        )

    # --- Department mutations ----------------------------------------

    async def department_created(self, session: AsyncSession, dept: Any) -> AuditEvent:
        return await self._record(
            session,
            event_type="department.created", action="create",
            resource_type="department", resource_id=dept.id, resource_label=dept.name,
            after=_dept_snapshot(dept),
        )

    async def department_updated(self, session: AsyncSession, dept: Any, changes: dict[str, list[Any]]) -> AuditEvent:
        return await self._record(
            session,
            event_type="department.updated", action="update",
            resource_type="department", resource_id=dept.id, resource_label=dept.name,
            changes=changes,
        )

    async def department_deleted(self, session: AsyncSession, dept_snapshot: dict[str, Any], dept_id: uuid.UUID, name: str) -> AuditEvent:
        return await self._record(
            session,
            event_type="department.deleted", action="delete",
            resource_type="department", resource_id=dept_id, resource_label=name,
            before=dept_snapshot,
        )

    # --- Auth events -------------------------------------------------

    async def login_succeeded(self, session: AsyncSession, user: Any) -> AuditEvent:
        return await self._record(
            session,
            event_type="auth.login_succeeded", action="login",
            resource_type="user", resource_id=user.id, resource_label=user.email,
        )

    async def login_failed(self, session: AsyncSession, email: str, reason: str) -> AuditEvent:
        return await self._record(
            session,
            event_type="auth.login_failed", action="login_failed",
            resource_type=None, resource_id=None, resource_label=None,
            metadata={"email": email, "reason": reason},
        )

    async def logout(self, session: AsyncSession, user: Any) -> AuditEvent:
        return await self._record(
            session,
            event_type="auth.logout", action="logout",
            resource_type="user", resource_id=user.id, resource_label=user.email,
        )

    async def password_changed(self, session: AsyncSession, user: Any) -> AuditEvent:
        return await self._record(
            session,
            event_type="auth.password_changed", action="password_changed",
            resource_type="user", resource_id=user.id, resource_label=user.email,
        )

    async def password_reset_requested(self, session: AsyncSession, user: Any) -> AuditEvent:
        return await self._record(
            session,
            event_type="auth.password_reset_requested", action="password_reset_requested",
            resource_type="user", resource_id=user.id, resource_label=user.email,
        )

    async def password_reset_consumed(self, session: AsyncSession, user: Any) -> AuditEvent:
        return await self._record(
            session,
            event_type="auth.password_reset_consumed", action="password_reset_consumed",
            resource_type="user", resource_id=user.id, resource_label=user.email,
        )

    async def session_revoked(self, session: AsyncSession, user: Any, session_id: uuid.UUID, by_admin: bool) -> AuditEvent:
        return await self._record(
            session,
            event_type="auth.session_revoked", action="session_revoked",
            resource_type="user", resource_id=user.id, resource_label=user.email,
            metadata={"session_id": str(session_id), "by_admin": by_admin},
        )

    # --- Self --------------------------------------------------------

    async def pruned(self, session: AsyncSession, cutoff: datetime, deleted_count: int, chunks: int) -> AuditEvent:
        return await self._record(
            session,
            event_type="audit.pruned", action="pruned",
            resource_type=None, resource_id=None, resource_label=None,
            metadata={"cutoff": cutoff.isoformat(), "deleted_count": deleted_count, "chunks": chunks},
        )


def _user_snapshot(user: Any) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "department_id": str(user.department_id) if user.department_id else None,
    }


def _role_snapshot(role: Any) -> dict[str, Any]:
    return {
        "id": str(role.id),
        "code": role.code,
        "name": role.name,
        "is_builtin": role.is_builtin,
        "is_superadmin": role.is_superadmin,
    }


def _dept_snapshot(dept: Any) -> dict[str, Any]:
    return {
        "id": str(dept.id),
        "name": dept.name,
        "parent_id": str(dept.parent_id) if dept.parent_id else None,
        "path": dept.path,
        "depth": dept.depth,
    }


audit = AuditService()  # module-level singleton; `from app.modules.audit.service import audit`
