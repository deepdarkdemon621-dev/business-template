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


async def test_login_bad_password_emits_failed_event(
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


async def test_login_unknown_email_emits_failed_event(
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
