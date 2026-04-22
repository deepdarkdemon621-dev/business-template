from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.modules.department.schemas import (
    DepartmentCreateIn,
    DepartmentMoveIn,
    DepartmentNode,
    DepartmentOut,
    DepartmentUpdateIn,
)


def test_create_requires_name_and_parent() -> None:
    with pytest.raises(ValidationError):
        DepartmentCreateIn(name="", parent_id=uuid.uuid4())
    ok = DepartmentCreateIn(name="Ops", parent_id=uuid.uuid4())
    assert ok.name == "Ops"


def test_update_name_only() -> None:
    assert DepartmentUpdateIn(name="New Name").name == "New Name"


def test_move_requires_new_parent() -> None:
    with pytest.raises(ValidationError):
        DepartmentMoveIn.model_validate({})
    assert DepartmentMoveIn(new_parent_id=uuid.uuid4()).new_parent_id is not None


def test_out_schema_fields() -> None:
    d = DepartmentOut(
        id=uuid.uuid4(),
        parent_id=None,
        name="Root",
        path="/root/",
        depth=0,
        is_active=True,
    )
    j = d.model_dump(by_alias=True)
    assert j["parentId"] is None  # camel alias
    assert j["isActive"] is True


def test_node_has_children() -> None:
    parent = DepartmentNode(
        id=uuid.uuid4(),
        parent_id=None,
        name="Root",
        path="/root/",
        depth=0,
        is_active=True,
        children=[],
    )
    assert parent.children == []
