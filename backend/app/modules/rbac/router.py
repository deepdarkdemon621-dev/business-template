from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.permissions import (
    SUPERADMIN_ALL,
    current_user_dep,
    get_user_permissions,
    require_perm,
)
from app.modules.auth.models import User
from app.modules.rbac import crud
from app.modules.rbac.schemas import DepartmentOut, MePermissionsOut

router = APIRouter(tags=["rbac"])


@router.get("/me/permissions", response_model=MePermissionsOut)
async def get_my_permissions(
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> MePermissionsOut:
    perms = await get_user_permissions(db, user)
    if perms is SUPERADMIN_ALL:
        return MePermissionsOut(is_superadmin=True, permissions={})
    assert isinstance(perms, dict)
    return MePermissionsOut(
        is_superadmin=False,
        permissions={k: v.value for k, v in perms.items()},
    )


@router.get(
    "/departments",
    response_model=list[DepartmentOut],
    dependencies=[Depends(require_perm("department:list"))],
)
async def list_departments_endpoint(
    db: AsyncSession = Depends(get_session),
) -> list[DepartmentOut]:
    items = await crud.list_departments(db)
    return [DepartmentOut.model_validate(i, from_attributes=True) for i in items]
