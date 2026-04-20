from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import Page, PageQuery, paginate
from app.core.permissions import (
    SUPERADMIN_ALL,
    apply_scope,
    current_user_dep,
    get_user_permissions,
    require_perm,
)
from app.modules.auth.models import User
from app.modules.rbac.models import Department, Role
from app.modules.rbac.schemas import DepartmentOut, MePermissionsOut, RoleOut

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
    response_model=Page[DepartmentOut],
    dependencies=[Depends(require_perm("department:list"))],
)
async def list_departments_endpoint(
    pq: Annotated[PageQuery, Depends()],
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Page[DepartmentOut]:
    perms = await get_user_permissions(db, user)
    stmt = select(Department).order_by(Department.depth, Department.name)
    stmt = apply_scope(stmt, user, "department:list", Department, perms)
    raw_page = await paginate(db, stmt, pq)
    items = [DepartmentOut.model_validate(i, from_attributes=True) for i in raw_page.items]
    return Page[DepartmentOut](
        items=items,
        total=raw_page.total,
        page=raw_page.page,
        size=raw_page.size,
        has_next=raw_page.has_next,
    )


@router.get(
    "/roles",
    response_model=Page[RoleOut],
    dependencies=[Depends(require_perm("role:list"))],
)
async def list_roles(
    pq: Annotated[PageQuery, Depends()],
    db: AsyncSession = Depends(get_session),
) -> Page[RoleOut]:
    stmt = select(Role).order_by(Role.name)
    raw = await paginate(db, stmt, pq)
    items = [RoleOut.model_validate(r, from_attributes=True) for r in raw.items]
    return Page[RoleOut](
        items=items,
        total=raw.total,
        page=raw.page,
        size=raw.size,
        has_next=raw.has_next,
    )
