from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageQuery
from app.modules.audit import crud
from app.modules.audit.context import AuditContext, audit_context
from app.modules.audit.schemas import AuditEventFilters
from app.modules.audit.service import audit


@pytest_asyncio.fixture
async def seeded_events(db_session: AsyncSession, db_audit_ctx: AuditContext):
    """Seed 4 audit events: user.created, user.updated, role.created, auth.login_failed.

    The first three are emitted under db_audit_ctx (real actor FK satisfied).
    login_failed is emitted under an anonymous context (actor_user_id=None) so
    that test_list_filter_by_actor can assert it is excluded from actor-filtered
    results.
    """
    u = SimpleNamespace(
        id=uuid.uuid4(),
        email="u@x",
        full_name="U",
        is_active=True,
        department_id=None,
    )
    r = SimpleNamespace(
        id=uuid.uuid4(),
        code="r1",
        name="R1",
        is_builtin=False,
        is_superadmin=False,
    )

    # Three events with the real actor.
    await audit.user_created(db_session, u)
    await audit.user_updated(db_session, u, {"full_name": ["A", "B"]})
    await audit.role_created(db_session, r)

    # login_failed should have null actor (auth endpoint runs without a
    # logged-in user). Temporarily replace the audit context with an
    # anonymous one for this single call.
    anon_ctx = AuditContext(actor_user_id=None, actor_ip="198.51.100.7", actor_user_agent="anon-ua")
    token = audit_context.set(anon_ctx)
    try:
        await audit.login_failed(db_session, "x@y.com", "bad_password")
    finally:
        audit_context.reset(token)

    await db_session.flush()
    return {"user": u, "role": r}


async def test_list_no_filter_returns_all(db_session: AsyncSession, seeded_events):
    pq = PageQuery(page=1, size=10)
    page = await crud.list_events(db_session, AuditEventFilters(), pq)
    assert page.total == 4


async def test_list_filter_by_event_type(db_session: AsyncSession, seeded_events):
    pq = PageQuery(page=1, size=10)
    page = await crud.list_events(
        db_session,
        AuditEventFilters(event_type=["user.created"]),
        pq,
    )
    assert page.total == 1
    assert page.items[0].event_type == "user.created"


async def test_list_filter_by_actor(db_session: AsyncSession, seeded_events, db_audit_ctx: AuditContext):
    pq = PageQuery(page=1, size=10)
    page = await crud.list_events(
        db_session,
        AuditEventFilters(actor_user_id=db_audit_ctx.actor_user_id),
        pq,
    )
    # login_failed was emitted with null actor — should be excluded.
    assert page.total == 3


async def test_list_filter_by_resource(db_session: AsyncSession, seeded_events):
    u = seeded_events["user"]
    pq = PageQuery(page=1, size=10)
    page = await crud.list_events(
        db_session,
        AuditEventFilters(resource_type="user", resource_id=u.id),
        pq,
    )
    assert page.total == 2  # user.created + user.updated


async def test_list_rejects_unknown_sort(db_session: AsyncSession, seeded_events):
    from app.core.errors import ProblemDetails

    pq = PageQuery(page=1, size=10, sort="banana")
    with pytest.raises(ProblemDetails) as exc:
        await crud.list_events(db_session, AuditEventFilters(), pq)
    assert exc.value.code == "audit.invalid-sort"


async def test_get_event_returns_single(db_session: AsyncSession, seeded_events):
    pq = PageQuery(page=1, size=10)
    page = await crud.list_events(db_session, AuditEventFilters(), pq)
    ev = await crud.get_event(db_session, page.items[0].id)
    assert ev is not None
    assert ev.id == page.items[0].id


async def test_get_event_returns_none_for_unknown(db_session: AsyncSession, seeded_events):
    ev = await crud.get_event(db_session, uuid.uuid4())
    assert ev is None
