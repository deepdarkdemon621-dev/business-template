from __future__ import annotations

import uuid

from pydantic import Field

from app.core.schemas import BaseSchema

# Email pattern kept intentionally simple — matches backend-wide convention
# (Plan 3 auth schemas also use plain `str` since `email-validator` is not
# a declared dependency).
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class PermissionOut(BaseSchema):
    id: uuid.UUID
    code: str
    resource: str
    action: str
    description: str | None = None


class RoleOut(BaseSchema):
    id: uuid.UUID
    code: str
    name: str
    is_builtin: bool
    is_superadmin: bool


class DepartmentOut(BaseSchema):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    path: str
    depth: int
    is_active: bool


class MePermissionsOut(BaseSchema):
    is_superadmin: bool
    permissions: dict[str, str]  # code -> scope


class GrantRoleIn(BaseSchema):
    email: str = Field(..., pattern=_EMAIL_PATTERN, max_length=254)
    role_code: str = Field(..., min_length=1, max_length=50)


class GrantRoleOut(BaseSchema):
    user_id: uuid.UUID
    role_code: str
    granted: bool  # True if new grant, False if already existed
