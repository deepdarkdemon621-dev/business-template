from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import EmailStr, Field

from app.core.schemas import BaseSchema


class AuditActor(BaseSchema):
    id: uuid.UUID
    email: EmailStr
    name: str


class AuditEventOut(BaseSchema):
    id: uuid.UUID
    occurred_at: datetime
    event_type: str
    action: str
    actor: AuditActor | None = None
    actor_ip: str | None = None
    actor_user_agent: str | None = None
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    resource_label: str | None = None
    summary: str


class AuditEventDetailOut(AuditEventOut):
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    changes: dict[str, Any] | None = None
    # Read from ORM attr `metadata_`, expose to JSON as `metadata`.
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_",
        serialization_alias="metadata",
    )


class AuditEventFilters(BaseSchema):
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    event_type: list[str] | None = None
    action: list[str] | None = None
    actor_user_id: uuid.UUID | None = None
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    q: str | None = None
