from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pydantic.alias_generators import to_camel


@dataclass
class RuleSpec:
    name: str  # camelCase keyword name, e.g. "mustMatch"
    params: dict[str, Any]  # camelCase field names for x-rules emission
    validate: Callable[[Any], None]


class FormRuleRegistry:
    _rules: dict[str, Callable[..., RuleSpec]] = {}

    @classmethod
    def register(cls, name: str, factory: Callable[..., RuleSpec]) -> None:
        if name in cls._rules:
            raise ValueError(f"rule {name!r} already registered")
        cls._rules[name] = factory

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._rules


def must_match(*, a: str, b: str) -> RuleSpec:
    def _check(instance: Any) -> None:
        va = getattr(instance, a)
        vb = getattr(instance, b)
        if va != vb:
            raise ValueError(f"{a} must equal {b}")

    return RuleSpec(
        name="mustMatch",
        params={"a": to_camel(a), "b": to_camel(b)},
        validate=_check,
    )


def date_order(*, start: str, end: str) -> RuleSpec:
    def _check(instance: Any) -> None:
        s = getattr(instance, start, None)
        e = getattr(instance, end, None)
        if s is None or e is None:
            return
        if not isinstance(s, (date, datetime)) or not isinstance(e, (date, datetime)):
            raise ValueError(f"{start} and {end} must be dates")
        if e <= s:
            raise ValueError(f"{end} must be after {start}")

    return RuleSpec(
        name="dateOrder",
        params={"start": to_camel(start), "end": to_camel(end)},
        validate=_check,
    )


def password_policy(field: str) -> RuleSpec:
    camel_field = to_camel(field)

    def _check(instance: Any) -> None:
        value = getattr(instance, field, "")
        if not isinstance(value, str):
            return
        if len(value) < 10:
            raise ValueError("Password must be at least 10 characters")
        has_letter = any(c.isalpha() for c in value)
        has_digit = any(c.isdigit() for c in value)
        if not has_letter or not has_digit:
            raise ValueError("Password must contain at least 1 letter and 1 digit")

    return RuleSpec(
        name="passwordPolicy",
        params={"field": camel_field},
        validate=_check,
    )


FormRuleRegistry.register("mustMatch", must_match)
FormRuleRegistry.register("dateOrder", date_order)
FormRuleRegistry.register("passwordPolicy", password_policy)
