from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, field_validator, model_serializer
from pydantic._internal._decorators import ModelValidatorDecoratorInfo, PydanticDescriptorProxy
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.core.form_rules import RuleSpec


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


def _build_rules_validator(rules: list[RuleSpec]):
    """Build a model validator function that runs all form rules."""

    def _validate_rules(self: Any) -> Any:
        for rule in rules:
            rule.validate(self)
        return self

    return _validate_rules


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        rules: list[RuleSpec] | None = cls.__dict__.get("__rules__")
        if not rules:
            return

        # --- 1. Inject Pydantic model validator via PydanticDescriptorProxy ---
        # DecoratorInfos.build() scans cls.__dict__ for PydanticDescriptorProxy
        # instances. By setting one as a class attribute, the validator is
        # discovered and registered automatically when Pydantic finalises the
        # model — no need to touch __pydantic_decorators__ directly.
        validator_fn = _build_rules_validator(rules)
        info = ModelValidatorDecoratorInfo(mode="after")
        proxy = PydanticDescriptorProxy(wrapped=validator_fn, decorator_info=info, shim=None)
        cls._form_rules_validator = proxy  # type: ignore[attr-defined]

        # --- 2. Inject json_schema_extra with x-rules metadata ---
        x_rules = [{"name": r.name, "params": r.params} for r in rules]
        existing_extra = cls.model_config.get("json_schema_extra")

        if existing_extra and callable(existing_extra):
            orig_fn = existing_extra

            def _merged_extra(
                schema: dict[str, Any],
                _orig: Any = orig_fn,
                _rules: list[dict[str, Any]] = x_rules,
            ) -> None:
                _orig(schema)
                schema["x-rules"] = _rules

            cls.model_config = {**cls.model_config, "json_schema_extra": _merged_extra}
        elif existing_extra and isinstance(existing_extra, dict):
            cls.model_config = {
                **cls.model_config,
                "json_schema_extra": {**existing_extra, "x-rules": x_rules},
            }
        else:
            cls.model_config = {**cls.model_config, "json_schema_extra": {"x-rules": x_rules}}

    @field_validator("*", mode="before")
    @classmethod
    def _reject_naive_datetime(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return v

    @model_serializer(mode="wrap", when_used="json")
    def _ser_model(self, handler):
        return _normalize_dt(handler(self))
