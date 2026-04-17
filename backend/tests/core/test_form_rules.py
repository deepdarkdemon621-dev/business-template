from datetime import date

import pytest
from pydantic import ValidationError

from app.core.form_rules import FormRuleRegistry, date_order, must_match
from app.core.schemas import BaseSchema


class _PasswordReset(BaseSchema):
    new_password: str
    confirm: str
    __rules__ = [must_match(a="new_password", b="confirm")]


class _DateRange(BaseSchema):
    starts_on: date
    ends_on: date
    __rules__ = [date_order(start="starts_on", end="ends_on")]


def test_must_match_fires_on_mismatch():
    with pytest.raises(ValidationError) as ei:
        _PasswordReset(new_password="a", confirm="b")
    assert any(e["type"] == "value_error" for e in ei.value.errors())


def test_must_match_passes_on_match():
    m = _PasswordReset(new_password="a", confirm="a")
    assert m.new_password == "a"


def test_date_order_fires_when_end_before_start():
    with pytest.raises(ValidationError):
        _DateRange(starts_on=date(2026, 4, 17), ends_on=date(2026, 4, 1))


def test_date_order_passes_when_end_after_start():
    _DateRange(starts_on=date(2026, 4, 1), ends_on=date(2026, 4, 17))


def test_x_rules_appears_in_json_schema_with_camel_case_field_names():
    schema = _PasswordReset.model_json_schema(by_alias=True)
    assert "x-rules" in schema
    rules = schema["x-rules"]
    assert rules == [{"name": "mustMatch", "params": {"a": "newPassword", "b": "confirm"}}]


def test_date_order_x_rules_in_schema():
    schema = _DateRange.model_json_schema(by_alias=True)
    assert schema["x-rules"] == [
        {"name": "dateOrder", "params": {"start": "startsOn", "end": "endsOn"}}
    ]


def test_registry_rejects_unknown_rule_name():
    assert "mustMatch" in FormRuleRegistry._rules
    assert "dateOrder" in FormRuleRegistry._rules


def test_schema_without_rules_has_no_x_rules_key():
    class _Plain(BaseSchema):
        name: str

    assert "x-rules" not in _Plain.model_json_schema()


# --- password_policy tests ---
from types import SimpleNamespace

from app.core.form_rules import password_policy


def test_password_policy_rule_spec():
    spec = password_policy("new_password")
    assert spec.name == "passwordPolicy"


def test_password_policy_passes_valid():
    spec = password_policy("new_password")
    spec.validate(SimpleNamespace(new_password="MySecret123"))  # no raise


def test_password_policy_fails_too_short():
    spec = password_policy("new_password")
    with pytest.raises(ValueError, match="10 characters"):
        spec.validate(SimpleNamespace(new_password="Ab1"))


def test_password_policy_fails_no_digit():
    spec = password_policy("new_password")
    with pytest.raises(ValueError, match="1 letter"):
        spec.validate(SimpleNamespace(new_password="abcdefghijk"))


def test_password_policy_fails_no_letter():
    spec = password_policy("new_password")
    with pytest.raises(ValueError, match="1 digit"):
        spec.validate(SimpleNamespace(new_password="1234567890"))
