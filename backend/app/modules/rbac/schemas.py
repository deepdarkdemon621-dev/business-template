from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.core.schemas import BaseSchema
from app.modules.rbac.constants import ScopeEnum

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


class RolePermissionItem(BaseSchema):
    permission_code: str = Field(..., min_length=1, max_length=100)
    scope: ScopeEnum


class RoleListOut(RoleOut):
    user_count: int
    permission_count: int
    updated_at: datetime


class RoleDetailOut(RoleOut):
    permissions: list[RolePermissionItem]
    user_count: int
    updated_at: datetime


class RoleCreateIn(BaseSchema):
    code: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(..., min_length=1, max_length=100)
    permissions: list[RolePermissionItem] = Field(default_factory=list)


class RoleUpdateIn(BaseSchema):
    code: str | None = Field(None, min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    name: str | None = Field(None, min_length=1, max_length=100)
    permissions: list[RolePermissionItem] | None = None


class RoleDeletedOut(BaseSchema):
    id: uuid.UUID
    deleted_user_roles: int
