import pytest
from pydantic import ValidationError

from app.modules.department.schemas import DepartmentOut
from app.modules.rbac.schemas import (
    GrantRoleIn,
    MePermissionsOut,
    PermissionOut,
    RoleCreateIn,
    RoleOut,
    RolePermissionItem,
    RoleUpdateIn,
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


def test_role_create_in_valid() -> None:
    payload = RoleCreateIn(code="editor", name="Editor")
    assert payload.code == "editor"
    assert payload.name == "Editor"
    assert payload.permissions == []


def test_role_create_in_rejects_bad_code() -> None:
    # Upper-case
    with pytest.raises(ValidationError):
        RoleCreateIn(code="Editor", name="Editor")
    # Starts with digit
    with pytest.raises(ValidationError):
        RoleCreateIn(code="1editor", name="Editor")
    # Too short
    with pytest.raises(ValidationError):
        RoleCreateIn(code="e", name="Editor")


def test_role_create_in_accepts_permission_items() -> None:
    payload = RoleCreateIn(
        code="viewer",
        name="Viewer",
        permissions=[
            RolePermissionItem(permission_code="user:read", scope="global"),
        ],
    )
    assert len(payload.permissions) == 1
    assert payload.permissions[0].permission_code == "user:read"


def test_role_update_in_all_optional() -> None:
    payload = RoleUpdateIn()
    assert payload.code is None
    assert payload.name is None
    assert payload.permissions is None  # None means metadata-only edit


def test_role_update_in_empty_permissions_list_means_clear_all() -> None:
    payload = RoleUpdateIn(permissions=[])
    assert payload.permissions == []
