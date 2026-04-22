from __future__ import annotations

import uuid
from typing import Self

from pydantic import Field, model_validator

from app.core.schemas import BaseSchema


class DepartmentCreateIn(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    parent_id: uuid.UUID


class DepartmentUpdateIn(BaseSchema):
    name: str = Field(min_length=1, max_length=100)


class DepartmentMoveIn(BaseSchema):
    new_parent_id: uuid.UUID


class DepartmentOut(BaseSchema):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    path: str
    depth: int
    is_active: bool


class DepartmentNode(DepartmentOut):
    children: list[DepartmentNode] = Field(default_factory=list)

    @model_validator(mode="after")
    def _freeze_children(self) -> Self:
        # Children list is built by the router, not by client input — no extra
        # invariants to enforce here. Keeping the validator as a hook for V2.
        return self


DepartmentNode.model_rebuild()
