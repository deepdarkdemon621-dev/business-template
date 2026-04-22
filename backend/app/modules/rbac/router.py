from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import Page, PageQuery, paginate
from app.core.permissions import (
    SUPERADMIN_ALL,
    current_user_dep,
    get_user_permissions,
    require_perm,
)
from app.modules.auth.models import User
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import MePermissionsOut, RoleOut

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
