from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import GuardViolationCtx, ProblemDetails
from app.core.guards import GuardViolationError
from app.core.pagination import Page, PageQuery, paginate
from app.core.permissions import (
    apply_scope,
    current_user_dep,
    get_user_permissions,
    load_in_scope,
    require_perm,
)
from app.modules.auth.models import User
from app.modules.rbac.models import Department
from app.modules.user.crud import build_list_users_stmt, get_roles_for_user
from app.modules.user.schemas import (
    DepartmentSummaryOut,
    RoleSummaryOut,
    UserCreateIn,
    UserDetailOut,
    UserOut,
    UserUpdateIn,
)
from app.modules.user.service import create_user, soft_delete_user, update_user

router = APIRouter(tags=["user"])


@router.get(
    "/users",
    response_model=Page[UserOut],
    dependencies=[Depends(require_perm("user:list"))],
)
async def list_users(
    pq: Annotated[PageQuery, Depends()],
    is_active: bool | None = Query(default=True),
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Page[UserOut]:
    perms = await get_user_permissions(db, user)
    stmt = build_list_users_stmt(is_active=is_active)
    stmt = apply_scope(stmt, user, "user:list", User, perms)
    raw = await paginate(db, stmt, pq)
    meta = raw.model_dump()
    meta.pop("items")
    return Page[UserOut](
        items=[UserOut.model_validate(i, from_attributes=True) for i in raw.items],
        **meta,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserDetailOut,
    dependencies=[Depends(require_perm("user:read"))],
)
async def get_user(
    user_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> UserDetailOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, User, user_id, user, "user:read", perms)
    roles = await get_roles_for_user(db, user_id)
    dept = await db.get(Department, target.department_id) if target.department_id else None
    return UserDetailOut(
        **UserOut.model_validate(target, from_attributes=True).model_dump(),
        roles=[RoleSummaryOut.model_validate(r, from_attributes=True) for r in roles],
        department=(
            DepartmentSummaryOut.model_validate(dept, from_attributes=True) if dept else None
        ),
    )


def _guard_to_problem(e: GuardViolationError) -> ProblemDetails:
    return ProblemDetails(
        code=e.code,
        status=403,
        detail=f"Operation blocked by guard: {e.code}.",
        guard_violation=GuardViolationCtx(guard=e.code, params=e.ctx),
    )


@router.post(
    "/users",
    response_model=UserOut,
    status_code=201,
    dependencies=[Depends(require_perm("user:create"))],
)
async def create_user_endpoint(
    payload: UserCreateIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> UserOut:
    new_user = await create_user(db, payload, actor=user)
    await db.commit()
    await db.refresh(new_user)
    return UserOut.model_validate(new_user, from_attributes=True)


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_perm("user:update"))],
)
async def update_user_endpoint(
    user_id: uuid.UUID,
    payload: UserUpdateIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> UserOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, User, user_id, user, "user:update", perms)
    try:
        updated = await update_user(db, target, payload, actor=user)
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    await db.refresh(updated)
    return UserOut.model_validate(updated, from_attributes=True)


@router.delete(
    "/users/{user_id}",
    status_code=204,
    dependencies=[Depends(require_perm("user:delete"))],
)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Response:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, User, user_id, user, "user:delete", perms)
    try:
        await soft_delete_user(db, target, actor=user)
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    return Response(status_code=204)
