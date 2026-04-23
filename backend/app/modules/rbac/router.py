from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import ProblemDetails
from app.core.pagination import Page, PageQuery, paginate
from app.core.permissions import (
    SUPERADMIN_ALL,
    current_user_dep,
    get_user_permissions,
    require_perm,
)
from app.modules.auth.models import User
from app.modules.rbac.crud import (
    count_role_users,
    get_role_with_permissions,
)
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole
from app.modules.rbac.schemas import (
    MePermissionsOut,
    PermissionOut,
    RoleCreateIn,
    RoleDeletedOut,
    RoleDetailOut,
    RoleListOut,
    RoleUpdateIn,
)
from app.modules.rbac.service import RoleService

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
    response_model=Page[RoleListOut],
    dependencies=[Depends(require_perm("role:list"))],
)
async def list_roles(
    pq: Annotated[PageQuery, Depends()],
    db: AsyncSession = Depends(get_session),
) -> Page[RoleListOut]:
    stmt = select(Role).order_by(Role.name)
    raw = await paginate(db, stmt, pq)
    role_ids = [r.id for r in raw.items]

    user_counts: dict = {}
    perm_counts: dict = {}
    if role_ids:
        uc_result = await db.execute(
            select(UserRole.role_id, func.count())
            .where(UserRole.role_id.in_(role_ids))
            .group_by(UserRole.role_id)
        )
        user_counts = dict(uc_result.all())
        pc_result = await db.execute(
            select(RolePermission.role_id, func.count())
            .where(RolePermission.role_id.in_(role_ids))
            .group_by(RolePermission.role_id)
        )
        perm_counts = dict(pc_result.all())

    items = [
        RoleListOut.model_validate(
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "is_builtin": r.is_builtin,
                "is_superadmin": r.is_superadmin,
                "user_count": int(user_counts.get(r.id, 0)),
                "permission_count": int(perm_counts.get(r.id, 0)),
                "updated_at": r.updated_at,
            }
        )
        for r in raw.items
    ]
    return Page[RoleListOut](
        items=items, total=raw.total, page=raw.page, size=raw.size, has_next=raw.has_next,
    )


@router.get(
    "/roles/{role_id}",
    response_model=RoleDetailOut,
    dependencies=[Depends(require_perm("role:read"))],
)
async def get_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> RoleDetailOut:
    try:
        role, items = await get_role_with_permissions(db, role_id)
    except LookupError as e:
        raise ProblemDetails(code="role.not-found", status=404, detail="Role not found.") from e
    user_count = await count_role_users(db, role.id)
    return RoleDetailOut.model_validate(
        {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "is_builtin": role.is_builtin,
            "is_superadmin": role.is_superadmin,
            "permissions": items,
            "user_count": user_count,
            "updated_at": role.updated_at,
        }
    )


@router.get(
    "/permissions",
    response_model=Page[PermissionOut],
    dependencies=[Depends(require_perm("permission:list"))],
)
async def list_permissions_endpoint(
    pq: Annotated[PageQuery, Depends()],
    db: AsyncSession = Depends(get_session),
) -> Page[PermissionOut]:
    stmt = select(Permission).order_by(Permission.resource, Permission.action)
    raw = await paginate(db, stmt, pq)
    items = [PermissionOut.model_validate(p, from_attributes=True) for p in raw.items]
    return Page[PermissionOut](
        items=items, total=raw.total, page=raw.page, size=raw.size, has_next=raw.has_next,
    )


async def _load_role_or_404(db: AsyncSession, role_id: uuid.UUID) -> Role:
    role = await db.get(Role, role_id)
    if role is None:
        raise ProblemDetails(code="role.not-found", status=404, detail="Role not found.")
    return role


@router.post(
    "/roles",
    response_model=RoleDetailOut,
    status_code=201,
    dependencies=[Depends(require_perm("role:create"))],
)
async def create_role_endpoint(
    payload: RoleCreateIn,
    db: AsyncSession = Depends(get_session),
) -> RoleDetailOut:
    role = await RoleService().create(db, payload)
    await db.commit()
    await db.refresh(role)
    _, items = await get_role_with_permissions(db, role.id)
    user_count = await count_role_users(db, role.id)
    return RoleDetailOut.model_validate(
        {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "is_builtin": role.is_builtin,
            "is_superadmin": role.is_superadmin,
            "permissions": items,
            "user_count": user_count,
            "updated_at": role.updated_at,
        }
    )


@router.patch(
    "/roles/{role_id}",
    response_model=RoleDetailOut,
    dependencies=[Depends(require_perm("role:update"))],
)
async def update_role_endpoint(
    role_id: uuid.UUID,
    payload: RoleUpdateIn,
    db: AsyncSession = Depends(get_session),
) -> RoleDetailOut:
    role = await _load_role_or_404(db, role_id)
    await RoleService().update(db, role, payload)
    await db.commit()
    await db.refresh(role)
    _, items = await get_role_with_permissions(db, role.id)
    user_count = await count_role_users(db, role.id)
    return RoleDetailOut.model_validate(
        {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "is_builtin": role.is_builtin,
            "is_superadmin": role.is_superadmin,
            "permissions": items,
            "user_count": user_count,
            "updated_at": role.updated_at,
        }
    )


@router.delete(
    "/roles/{role_id}",
    response_model=RoleDeletedOut,
    dependencies=[Depends(require_perm("role:delete"))],
)
async def delete_role_endpoint(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> RoleDeletedOut:
    role = await _load_role_or_404(db, role_id)
    deleted_user_roles = await RoleService().delete(db, role)
    await db.commit()
    return RoleDeletedOut.model_validate({"id": role_id, "deleted_user_roles": deleted_user_roles})
