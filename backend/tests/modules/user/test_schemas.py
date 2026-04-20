from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.user.schemas import (
    RoleSummaryOut,
    UserCreateIn,
    UserDetailOut,
    UserOut,
    UserUpdateIn,
)


def test_user_create_in_requires_password_policy():
    with pytest.raises(ValidationError) as ei:
        UserCreateIn(email="a@b.com", password="short1", full_name="A")
    assert "Password" in str(ei.value)


def test_user_create_in_accepts_valid_payload():
    u = UserCreateIn(
        email="a@b.com",
        password="LongEnough123",
        full_name="Alice",
    )
    assert u.must_change_password is True  # default


def test_user_create_in_rejects_empty_full_name():
    with pytest.raises(ValidationError):
        UserCreateIn(email="a@b.com", password="LongEnough123", full_name="")


def test_user_update_in_all_fields_optional():
    u = UserUpdateIn()
    assert u.full_name is None
    assert u.is_active is None


def test_user_out_excludes_password_hash():
    assert "password_hash" not in UserOut.model_fields
    assert "passwordHash" not in UserOut.model_json_schema()["properties"]


def test_role_summary_out_shape():
    r = RoleSummaryOut(id="00000000-0000-0000-0000-000000000001", code="admin", name="Admin")
    dumped = r.model_dump(by_alias=True)
    assert set(dumped.keys()) == {"id", "code", "name"}


def test_user_detail_out_has_roles_list():
    assert UserDetailOut.model_fields["roles"].annotation == list[RoleSummaryOut]
