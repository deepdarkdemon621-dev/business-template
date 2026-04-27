from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.audit.context import AuditContext, audit_context
from app.modules.rbac.models import Role, UserRole
from app.modules.auth.models import User
from tests.modules.rbac.conftest import member_token  # noqa: F401
from tests.modules.user.conftest import login


@pytest.fixture
def audit_ctx() -> Generator[AuditContext]:
    """Sync audit context with a random actor_user_id.

    NOTE: Only use this fixture in tests that do NOT write to the DB (e.g.
    purely in-memory / sync tests). For async DB tests that insert AuditEvent
    rows, use `db_audit_ctx` instead — it creates a real User row to satisfy
    the audit_events.actor_user_id FK constraint (provided by root conftest).
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


@pytest.fixture
def anon_audit_ctx() -> Generator[AuditContext]:
    ctx = AuditContext(actor_user_id=None, actor_ip="198.51.100.7", actor_user_agent="anon-ua")
    token = audit_context.set(ctx)
    try:
        yield ctx
    finally:
        audit_context.reset(token)


@pytest_asyncio.fixture
async def superadmin_token(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str]:
    """User assigned the seeded 'superadmin' role (bypasses all permission checks)."""
    role = (await db_session.execute(select(Role).where(Role.code == "superadmin"))).scalar_one()
    u = User(
        email="audit-superadmin@ex.com",
        password_hash=hash_password("pw-aaa111"),
        full_name="Audit Superadmin",
    )
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=role.id))
    await db_session.commit()
    token = await login(client_with_db, "audit-superadmin@ex.com", "pw-aaa111")
    return client_with_db, token


@pytest_asyncio.fixture
async def seeded_user_password(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[str, str]:
    """Plain user (no role), returns (email, plaintext_password). Use for login tests."""
    email = "audit-loginsubject@example.com"
    password = "test-password-aaa111"
    u = User(
        email=email,
        password_hash=hash_password(password),
        full_name="Login Subject",
    )
    db_session.add(u)
    await db_session.commit()
    return (email, password)


@pytest_asyncio.fixture
async def logged_in_user_token(
    client_with_db: AsyncClient, seeded_user_password: tuple[str, str]
) -> str:
    """Returns just the access token for a freshly-created plain user."""
    email, password = seeded_user_password
    return await login(client_with_db, email, password)
