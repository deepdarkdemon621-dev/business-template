from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.core.form_rules import password_policy
from app.core.schemas import BaseSchema


class RoleSummaryOut(BaseSchema):
    id: uuid.UUID
    code: str
    name: str


class DepartmentSummaryOut(BaseSchema):
    id: uuid.UUID
    name: str
    path: str


class UserCreateIn(BaseSchema):
    __rules__ = [password_policy(field="password")]

    email: EmailStr
    password: str
    full_name: str = Field(min_length=1, max_length=100)
    department_id: uuid.UUID | None = None
    must_change_password: bool = True


class UserUpdateIn(BaseSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    department_id: uuid.UUID | None = None
    is_active: bool | None = None


class UserOut(BaseSchema):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    department_id: uuid.UUID | None
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class UserDetailOut(UserOut):
    roles: list[RoleSummaryOut] = Field(default_factory=list)
    department: DepartmentSummaryOut | None = None
