"""Integration tests: AuthService mutation paths emit audit events.

These tests call real HTTP endpoints (via client_with_db) and then query
the audit_events table directly to verify the rows were written.

NOTE on session isolation:
- Successful-login audit rows use the request session (committed by the router
  after the service returns) — they ARE visible in db_session because
  client_with_db overrides get_session with db_session.
- Failed-login audit rows use _emit_failed_login_independently, which opens a
  FRESH session and commits independently.  Those rows are NOT inside the
  db_session transaction, so they must be queried via a separate direct session
  (direct_session fixture below).
"""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session as _session_factory
from app.modules.audit.models import AuditEvent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _login(client: AsyncClient, email: str, password: str, **kwargs) -> int:
    """POST /auth/login, return status code."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        **kwargs,
    )
    return resp.status_code


async def _get_audit_event_in_session(
    db: AsyncSession, event_type: str
) -> AuditEvent | None:
    """Query audit events within the provided session."""
    result = await db.execute(
        select(AuditEvent).where(AuditEvent.event_type == event_type)
    )
    return result.scalar_one_or_none()


async def _get_failed_login_direct(email: str) -> AuditEvent | None:
    """Query a login_failed event for a specific email via a fresh committed session.

    Uses JSONB containment so we can distinguish rows from different test emails.
    """
    from sqlalchemy.dialects.postgresql import JSONB

    async with _session_factory() as session:
        result = await session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "auth.login_failed",
                AuditEvent.metadata_.cast(JSONB)["email"].astext == email,
            )
        )
        return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_login_success_emits_event_and_updates_last_login_at(
    client_with_db: AsyncClient,
    db_session: AsyncSession,
    seeded_user_password: tuple[str, str],
) -> None:
    """Successful login writes auth.login_succeeded and sets last_login_at."""
    email, password = seeded_user_password
    status = await _login(
        client_with_db, email, password, headers={"User-Agent": "pytest"}
    )
    assert status == 200, f"Expected 200, got {status}"

    # Audit event persisted (in same request session — visible via db_session)
    ev = await _get_audit_event_in_session(db_session, "auth.login_succeeded")
    assert ev is not None, "auth.login_succeeded event not found"
    assert ev.resource_label == email
    assert ev.actor_user_agent == "pytest"

    # last_login_at updated
    from app.modules.auth.models import User as _User

    user = (
        await db_session.execute(select(_User).where(_User.email == email))
    ).scalar_one()
    assert user.last_login_at is not None, "last_login_at was not set"


async def test_login_bad_password_emits_login_failed(
    client_with_db: AsyncClient,
    seeded_user_password: tuple[str, str],
) -> None:
    """Wrong password writes auth.login_failed with reason=bad_password.

    Uses a direct (not rollback) session because the audit row is committed
    independently by _emit_failed_login_independently.
    """
    email, _ = seeded_user_password
    status = await _login(client_with_db, email, "WRONG-password-999")
    assert status == 401, f"Expected 401, got {status}"

    ev = await _get_failed_login_direct(email)
    assert ev is not None, "auth.login_failed event not found"
    assert ev.metadata_["email"] == email
    assert ev.metadata_["reason"] == "bad_password"


async def test_login_unknown_email_emits_login_failed_unknown_email(
    client_with_db: AsyncClient,
) -> None:
    """Unknown e-mail writes auth.login_failed with reason=unknown_email.

    Uses a direct (not rollback) session because the audit row is committed
    independently by _emit_failed_login_independently.
    """
    unknown_email = "nobody-unknown-xyz789@example.com"
    status = await _login(client_with_db, unknown_email, "doesnt-matter")
    assert status == 401, f"Expected 401, got {status}"

    ev = await _get_failed_login_direct(unknown_email)
    assert ev is not None, "auth.login_failed event not found"
    assert ev.metadata_["email"] == unknown_email
    assert ev.metadata_["reason"] == "unknown_email"


async def test_logout_emits_audit_event(
    client_with_db: AsyncClient,
    db_session: AsyncSession,
    logged_in_user_token: str,
) -> None:
    """Logout writes auth.logout event."""
    resp = await client_with_db.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {logged_in_user_token}"},
    )
    assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

    ev = await _get_audit_event_in_session(db_session, "auth.logout")
    assert ev is not None, "auth.logout event not found"


# ---------------------------------------------------------------------------
# Role audit tests
# ---------------------------------------------------------------------------


async def test_role_create_emits_event(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """POST /roles writes role.created audit event."""
    client, token = superadmin_token
    res = await client.post(
        "/api/v1/roles",
        json={"code": "auditor_create_t9", "name": "Auditor T9"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "role.created",
                AuditEvent.resource_label == "auditor_create_t9",
            )
        )
    ).scalar_one()
    assert ev.actor_user_id is not None
    assert ev.after["code"] == "auditor_create_t9"


async def test_role_update_emits_changes(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """PATCH /roles/{id} writes role.updated audit event with field diff."""
    client, token = superadmin_token
    res = await client.post(
        "/api/v1/roles",
        json={"code": "ed1_t9", "name": "Old Name T9"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    role_id = res.json()["id"]
    res = await client.patch(
        f"/api/v1/roles/{role_id}",
        json={"name": "New Name T9"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "role.updated",
                AuditEvent.resource_label == "ed1_t9",
            )
        )
    ).scalar_one()
    assert ev.changes == {"name": ["Old Name T9", "New Name T9"]}


async def test_role_permissions_update_emits_added_removed(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """Replacing permissions writes role.permissions_updated with added/removed lists."""
    client, token = superadmin_token
    res = await client.post(
        "/api/v1/roles",
        json={
            "code": "permtest_t9",
            "name": "Perm Test T9",
            "permissions": [{"permissionCode": "user:read", "scope": "global"}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    role_id = res.json()["id"]
    res = await client.patch(
        f"/api/v1/roles/{role_id}",
        json={"permissions": [{"permissionCode": "user:list", "scope": "global"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "role.permissions_updated",
                AuditEvent.resource_label == "permtest_t9",
            )
        )
    ).scalar_one()
    added_codes = [a["permission_code"] for a in ev.metadata_["added"]]
    removed_codes = [r["permission_code"] for r in ev.metadata_["removed"]]
    assert "user:list" in added_codes
    assert "user:read" in removed_codes


async def test_role_permissions_scope_only_change_emits_event(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """A scope-only change (same code, new scope) emits role.permissions_updated with scope_changed."""
    client, token = superadmin_token
    res = await client.post(
        "/api/v1/roles",
        json={
            "code": "scope_test_t9",
            "name": "Scope Test T9",
            "permissions": [{"permissionCode": "user:read", "scope": "global"}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    role_id = res.json()["id"]
    res = await client.patch(
        f"/api/v1/roles/{role_id}",
        json={"permissions": [{"permissionCode": "user:read", "scope": "dept_tree"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "role.permissions_updated",
                AuditEvent.resource_label == "scope_test_t9",
            )
        )
    ).scalar_one()
    sc = ev.metadata_["scope_changed"]
    assert len(sc) == 1
    assert sc[0]["permission_code"] == "user:read"
    assert sc[0]["from_scope"] == "global"
    assert sc[0]["to_scope"] == "dept_tree"
    # added/removed must be empty for a scope-only change
    assert ev.metadata_["added"] == []
    assert ev.metadata_["removed"] == []


async def test_role_delete_emits_before_snapshot(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """DELETE /roles/{id} writes role.deleted with before-snapshot."""
    client, token = superadmin_token
    res = await client.post(
        "/api/v1/roles",
        json={"code": "tbd_t9", "name": "To Be Deleted T9"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    role_id = res.json()["id"]
    res = await client.delete(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "role.deleted",
                AuditEvent.resource_label == "tbd_t9",
            )
        )
    ).scalar_one()
    assert ev.before["code"] == "tbd_t9"


# ---------------------------------------------------------------------------
# User audit tests (Task 10)
# ---------------------------------------------------------------------------


async def test_user_create_emits_event(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """POST /users writes user.created with no password fields in after-snapshot."""
    client, token = superadmin_token
    res = await client.post(
        "/api/v1/users",
        json={"email": "new_t10@x.com", "fullName": "N T10", "password": "Test12345!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "user.created",
                AuditEvent.resource_label == "new_t10@x.com",
            )
        )
    ).scalar_one()
    assert ev.actor_user_id is not None
    assert "password" not in (ev.after or {})
    assert "password_hash" not in (ev.after or {})


async def test_user_update_only_changed_fields(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """PATCH /users/{id} writes user.updated with only the changed field diff."""
    client, token = superadmin_token
    res = await client.post(
        "/api/v1/users",
        json={"email": "upd_t10@x.com", "fullName": "Old T10", "password": "Test12345!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    user_id = res.json()["id"]
    res = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"fullName": "New T10"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "user.updated",
                AuditEvent.resource_label == "upd_t10@x.com",
            )
        )
    ).scalar_one()
    assert list(ev.changes.keys()) == ["full_name"]


async def test_user_delete_snapshot(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """DELETE /users/{id} writes user.deleted with before-snapshot (is_active=True)."""
    client, token = superadmin_token
    res = await client.post(
        "/api/v1/users",
        json={"email": "tbd_t10@x.com", "fullName": "T T10", "password": "Test12345!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    user_id = res.json()["id"]
    res = await client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204, res.text
    ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "user.deleted",
                AuditEvent.resource_label == "tbd_t10@x.com",
            )
        )
    ).scalar_one()
    assert ev.before["email"] == "tbd_t10@x.com"
    assert ev.before["is_active"] is True


async def test_user_role_assign_revoke_emits_events(
    superadmin_token: tuple,
    db_session: AsyncSession,
) -> None:
    """POST/DELETE /users/{id}/roles/{role_id} emit user.role_assigned / user.role_revoked."""
    from sqlalchemy import select as _select

    from app.modules.rbac.models import Role

    client, token = superadmin_token
    # Create user
    res = await client.post(
        "/api/v1/users",
        json={"email": "role_t10@x.com", "fullName": "R T10", "password": "Test12345!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    user_id = res.json()["id"]

    # Look up the seeded 'member' role id
    role_id = str(
        (await db_session.execute(_select(Role).where(Role.code == "member"))).scalar_one().id
    )

    # Assign role
    res = await client.post(
        f"/api/v1/users/{user_id}/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204, res.text
    assign_ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "user.role_assigned",
                AuditEvent.resource_label == "role_t10@x.com",
            )
        )
    ).scalar_one()
    assert assign_ev.metadata_["role_code"] == "member"

    # Revoke role
    res = await client.delete(
        f"/api/v1/users/{user_id}/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204, res.text
    revoke_ev = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "user.role_revoked",
                AuditEvent.resource_label == "role_t10@x.com",
            )
        )
    ).scalar_one()
    assert revoke_ev.metadata_["role_code"] == "member"
