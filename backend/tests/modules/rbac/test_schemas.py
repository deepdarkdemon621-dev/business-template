import pytest
from pydantic import ValidationError

from app.modules.department.schemas import DepartmentOut
from app.modules.rbac.schemas import (
    GrantRoleIn,
    MePermissionsOut,
    PermissionOut,
    RoleOut,
)

# Ensure the unused imports are validated as importable (module-level side effect).
_ = (PermissionOut, RoleOut, DepartmentOut)


def test_grant_role_in_rejects_invalid_email():
    with pytest.raises(ValidationError):
        GrantRoleIn(email="not-an-email", role_code="admin")


def test_grant_role_in_rejects_empty_role_code():
    with pytest.raises(ValidationError):
        GrantRoleIn(email="x@y.com", role_code="")


def test_me_permissions_out_shape():
    out = MePermissionsOut(is_superadmin=False, permissions={"user:read": "own"})
    dumped = out.model_dump(by_alias=True)
    assert "isSuperadmin" in dumped
    assert dumped["permissions"]["user:read"] == "own"
