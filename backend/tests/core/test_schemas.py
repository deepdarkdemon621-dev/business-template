from datetime import UTC, datetime

import pytest

from app.core.schemas import BaseSchema


class _User(BaseSchema):
    id: int
    display_name: str
    created_at: datetime


def test_serializes_to_camel_case():
    u = _User(id=1, display_name="Ada", created_at=datetime(2026, 4, 17, tzinfo=UTC))
    data = u.model_dump(by_alias=True, mode="json")
    assert data == {"id": 1, "displayName": "Ada", "createdAt": "2026-04-17T00:00:00Z"}


def test_accepts_both_camel_and_snake_on_input():
    snake = _User.model_validate(
        {"id": 1, "display_name": "Ada", "created_at": "2026-04-17T00:00:00Z"}
    )
    camel = _User.model_validate(
        {"id": 1, "displayName": "Ada", "createdAt": "2026-04-17T00:00:00Z"}
    )
    assert snake.display_name == "Ada" == camel.display_name


def test_from_attributes_reads_arbitrary_object():
    class _Row:
        id = 1
        display_name = "Ada"
        created_at = datetime(2026, 4, 17, tzinfo=UTC)

    u = _User.model_validate(_Row())
    assert u.display_name == "Ada"


def test_non_utc_datetime_keeps_explicit_offset():
    from datetime import timedelta, timezone

    tz = timezone(timedelta(hours=9))
    u = _User(id=1, display_name="Ada", created_at=datetime(2026, 4, 17, tzinfo=tz))
    data = u.model_dump(by_alias=True, mode="json")
    assert data["createdAt"].endswith("+09:00")


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        _User(id=1, display_name="Ada", created_at=datetime(2026, 4, 17))
