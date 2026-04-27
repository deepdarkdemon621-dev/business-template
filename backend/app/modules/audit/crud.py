# backend/app/modules/audit/crud.py
from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemDetails
from app.core.pagination import Page, PageQuery, paginate
from app.modules.audit.models import AuditEvent
from app.modules.audit.schemas import AuditEventFilters
from app.modules.auth.models import User


async def create_event(session: AsyncSession, **fields: Any) -> AuditEvent:
    event = AuditEvent(**fields)
    session.add(event)
    return event


def _apply_filters(stmt: Select, f: AuditEventFilters) -> Select:
    if f.occurred_from is not None:
        stmt = stmt.where(AuditEvent.occurred_at >= f.occurred_from)
    if f.occurred_to is not None:
        stmt = stmt.where(AuditEvent.occurred_at <= f.occurred_to)
    if f.event_type:
        stmt = stmt.where(AuditEvent.event_type.in_(f.event_type))
    if f.action:
        stmt = stmt.where(AuditEvent.action.in_(f.action))
    if f.actor_user_id is not None:
        stmt = stmt.where(AuditEvent.actor_user_id == f.actor_user_id)
    if f.resource_type is not None:
        stmt = stmt.where(AuditEvent.resource_type == f.resource_type)
    if f.resource_id is not None:
        stmt = stmt.where(AuditEvent.resource_id == f.resource_id)
    if f.q:
        stmt = stmt.where(AuditEvent.resource_label.ilike(f"%{f.q}%"))
    return stmt


async def list_events(
    session: AsyncSession,
    filters: AuditEventFilters,
    pq: PageQuery,
) -> Page[AuditEvent]:
    stmt = select(AuditEvent)
    stmt = _apply_filters(stmt, filters)
    sort = pq.sort or "-occurred_at"
    if sort == "-occurred_at":
        stmt = stmt.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
    elif sort == "occurred_at":
        stmt = stmt.order_by(AuditEvent.occurred_at.asc(), AuditEvent.id.asc())
    elif sort == "-id":
        stmt = stmt.order_by(AuditEvent.id.desc())
    elif sort == "id":
        stmt = stmt.order_by(AuditEvent.id.asc())
    else:
        raise ProblemDetails(code="audit.invalid-sort", status=400, detail=f"Invalid sort: {sort}")
    return await paginate(session, stmt, pq)


async def get_event(session: AsyncSession, event_id: uuid.UUID) -> AuditEvent | None:
    stmt = select(AuditEvent).where(AuditEvent.id == event_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_actors(session: AsyncSession, user_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, User]:
    if not user_ids:
        return {}
    stmt = select(User).where(User.id.in_(user_ids))
    result = await session.execute(stmt)
    return {u.id: u for u in result.scalars().all()}
