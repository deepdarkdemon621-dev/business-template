from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_serializer
from pydantic.alias_generators import to_camel


def _normalize_dt(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        s = value.isoformat()
        return s.replace("+00:00", "Z") if s.endswith("+00:00") else s
    if isinstance(value, dict):
        return {k: _normalize_dt(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_dt(v) for v in value]
    return value


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    @field_validator("*", mode="before")
    @classmethod
    def _reject_naive_datetime(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return v

    @model_serializer(mode="wrap", when_used="json")
    def _ser_model(self, handler):
        return _normalize_dt(handler(self))
