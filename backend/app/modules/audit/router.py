# backend/app/modules/audit/router.py
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import ProblemDetails
from app.core.pagination import Page, PageQuery
from app.core.permissions import require_perm
from app.modules.audit import crud
from app.modules.audit.context import bind_audit_context
from app.modules.audit.schemas import (
    AuditActor,
    AuditEventDetailOut,
    AuditEventFilters,
    AuditEventOut,
)
from app.modules.audit.summaries import render_summary

router = APIRouter(prefix="/audit-events", tags=["audit"])


def _filters(
    occurred_from: datetime | None = Query(None),
    occurred_to: datetime | None = Query(None),
    event_type: list[str] | None = Query(None),
    action: list[str] | None = Query(None),
    actor_user_id: uuid.UUID | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: uuid.UUID | None = Query(None),
    q: str | None = Query(None),
) -> AuditEventFilters:
    return AuditEventFilters(
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        event_type=event_type,
        action=action,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        q=q,
    )


@router.get(
    "",
    response_model=Page[AuditEventOut],
    dependencies=[Depends(require_perm("audit:list")), Depends(bind_audit_context)],
)
async def list_audit_events(
    filters: AuditEventFilters = Depends(_filters),
    pq: PageQuery = Depends(),
    session: AsyncSession = Depends(get_session),
) -> Page[AuditEventOut]:
    raw = await crud.list_events(session, filters, pq)
    actor_ids = {ev.actor_user_id for ev in raw.items if ev.actor_user_id is not None}
    actors = await crud.get_actors(session, list(actor_ids))
    items = [
        AuditEventOut(
            id=ev.id,
            occurred_at=ev.occurred_at,
            event_type=ev.event_type,
            action=ev.action,
            actor=(
                AuditActor(
                    id=actors[ev.actor_user_id].id,
                    email=actors[ev.actor_user_id].email,
                    name=actors[ev.actor_user_id].full_name,
                )
                if ev.actor_user_id is not None and ev.actor_user_id in actors
                else None
            ),
            actor_ip=str(ev.actor_ip) if ev.actor_ip else None,
            actor_user_agent=ev.actor_user_agent,
            resource_type=ev.resource_type,
            resource_id=ev.resource_id,
            resource_label=ev.resource_label,
            summary=render_summary(ev.event_type, ev.action, ev.resource_label, ev.metadata_, ev.changes),
        )
        for ev in raw.items
    ]
    return Page[AuditEventOut](
        items=items,
        total=raw.total,
        page=raw.page,
        size=raw.size,
        has_next=raw.has_next,
    )


@router.get(
    "/{event_id}",
    response_model=AuditEventDetailOut,
    dependencies=[Depends(require_perm("audit:read")), Depends(bind_audit_context)],
)
async def get_audit_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> AuditEventDetailOut:
    ev = await crud.get_event(session, event_id)
    if ev is None:
        raise ProblemDetails(code="audit.not-found", status=404, detail="Audit event not found.")
    actor = None
    if ev.actor_user_id is not None:
        actors = await crud.get_actors(session, [ev.actor_user_id])
        a = actors.get(ev.actor_user_id)
        if a is not None:
            actor = AuditActor(id=a.id, email=a.email, name=a.full_name)
    return AuditEventDetailOut(
        id=ev.id,
        occurred_at=ev.occurred_at,
        event_type=ev.event_type,
        action=ev.action,
        actor=actor,
        actor_ip=str(ev.actor_ip) if ev.actor_ip else None,
        actor_user_agent=ev.actor_user_agent,
        resource_type=ev.resource_type,
        resource_id=ev.resource_id,
        resource_label=ev.resource_label,
        summary=render_summary(ev.event_type, ev.action, ev.resource_label, ev.metadata_, ev.changes),
        before=ev.before,
        after=ev.after,
        changes=ev.changes,
        metadata_=ev.metadata_,  # validation_alias="metadata_" — must use alias, serialized as "metadata"
    )
