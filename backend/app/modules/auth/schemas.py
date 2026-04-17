from __future__ import annotations

import uuid
from datetime import datetime

from app.core.form_rules import must_match
from app.core.schemas import BaseSchema


class LoginRequest(BaseSchema):
    email: str
    password: str
    captcha: str | None = None


class TokenResponse(BaseSchema):
    access_token: str
    expires_in: int


class UserRead(BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str
    department_id: uuid.UUID | None
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseSchema):
    access_token: str
    expires_in: int
    user: UserRead
    must_change_password: bool


class PasswordChangeRequest(BaseSchema):
    __rules__ = [must_match(a="new_password", b="confirm")]

    current_password: str
    new_password: str
    confirm: str


class PasswordResetRequest(BaseSchema):
    email: str


class PasswordResetConfirmRequest(BaseSchema):
    __rules__ = [must_match(a="new_password", b="confirm")]

    token: str
    new_password: str
    confirm: str


class SessionRead(BaseSchema):
    id: uuid.UUID
    device_label: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    is_current: bool
