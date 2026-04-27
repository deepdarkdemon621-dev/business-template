# backend/app/modules/audit/context.py
"""Request-scoped audit actor context.

This is the one place in the codebase that uses a contextvar instead of
request.state. Reason: AuditService methods are called from deep inside
other service layers (RoleService, UserService, AuthService) which do not
receive the FastAPI Request object. A contextvar is the idiomatic way to
make per-request data reachable from code that cannot accept dependencies.

NEVER start a detached asyncio.Task inside a request handler and expect the
contextvar to propagate — copy_context() takes a snapshot at task-creation
time and drift is possible. No current code does this; audit events should
always be emitted synchronously in the request handler.
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class AuditContext:
    actor_user_id: uuid.UUID | None
    actor_ip: str | None
    actor_user_agent: str | None


audit_context: ContextVar[AuditContext | None] = ContextVar("audit_context", default=None)


def _extract_ip(request: Request) -> str | None:
    # No TRUSTED_PROXIES config yet; take raw client host. If/when a proxy
    # sits in front, introduce TRUSTED_PROXIES parsing here. Keep this
    # function the single extraction point.
    return request.client.host if request.client else None


def _extract_ua(request: Request) -> str | None:
    ua = request.headers.get("User-Agent")
    return ua[:512] if ua else None


async def bind_audit_context(request: Request) -> None:
    """Dependency: populates audit_context for the current request.

    Must run AFTER the auth dependency so the actor is known. For
    unauthenticated endpoints (login), actor_user_id is None — IP and UA
    are still captured.
    """
    actor_user_id: uuid.UUID | None = None
    user = getattr(request.state, "user", None)
    if user is not None:
        actor_user_id = user.id
    audit_context.set(
        AuditContext(
            actor_user_id=actor_user_id,
            actor_ip=_extract_ip(request),
            actor_user_agent=_extract_ua(request),
        )
    )


def get_context() -> AuditContext:
    """Read current audit context. Raises if unset (programmer error)."""
    ctx = audit_context.get()
    if ctx is None:
        raise RuntimeError(
            "audit_context is unset. Did you forget to add bind_audit_context as a route dependency?"
        )
    return ctx


def set_context_for_test(ctx: AuditContext) -> None:
    """Test-only helper. Never call from production code."""
    audit_context.set(ctx)
