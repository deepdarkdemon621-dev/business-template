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
from app.modules.audit.context import bind_audit_context
from app.modules.auth.models import User
from app.modules.department.crud import (
    build_list_flat_stmt,
    create_department,
    list_scoped_tree_rows,
    soft_delete_department,
    update_department,
)
from app.modules.department.schemas import (
    DepartmentCreateIn,
    DepartmentMoveIn,
    DepartmentNode,
    DepartmentOut,
    DepartmentUpdateIn,
)
from app.modules.department.service import DepartmentService
from app.modules.rbac.models import Department

router = APIRouter(tags=["department"])


def _guard_to_problem(e: GuardViolationError) -> ProblemDetails:
    # Department guard codes are all 409 (conflict with existing state).
    return ProblemDetails(
        code=e.code,
        status=409,
        detail=f"Operation blocked by guard: {e.code}.",
        guard_violation=GuardViolationCtx(guard=e.code, params=e.ctx),
    )


def _build_tree(rows: list[Department]) -> list[DepartmentNode]:
    by_id: dict[uuid.UUID, DepartmentNode] = {
        r.id: DepartmentNode.model_validate(r, from_attributes=True) for r in rows
    }
    roots: list[DepartmentNode] = []
    for r in rows:
        node = by_id[r.id]
        if r.parent_id is not None and r.parent_id in by_id:
            by_id[r.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


@router.get(
    "/departments",
    response_model=Page[DepartmentOut],
    dependencies=[Depends(require_perm("department:read"))],
)
async def list_departments_endpoint(
    pq: Annotated[PageQuery, Depends()],
    is_active: bool | None = Query(default=True),
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Page[DepartmentOut]:
    perms = await get_user_permissions(db, user)
    stmt = build_list_flat_stmt(is_active=is_active)
    stmt = apply_scope(stmt, user, "department:read", Department, perms)
    raw = await paginate(db, stmt, pq)
    items = [DepartmentOut.model_validate(i, from_attributes=True) for i in raw.items]
    return Page[DepartmentOut](
        items=items,
        total=raw.total,
        page=raw.page,
        size=raw.size,
        has_next=raw.has_next,
    )


@router.get(
    "/departments/tree",
    response_model=list[DepartmentNode],
    dependencies=[Depends(require_perm("department:read"))],
)
async def tree_departments_endpoint(
    include_inactive: bool = Query(default=False, alias="includeInactive"),
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> list[DepartmentNode]:
    perms = await get_user_permissions(db, user)
    rows = await list_scoped_tree_rows(
        db, user=user, perms=perms, include_inactive=include_inactive
    )
    return _build_tree(rows)


@router.get(
    "/departments/{dept_id}",
    response_model=DepartmentOut,
    dependencies=[Depends(require_perm("department:read"))],
)
async def get_department_endpoint(
    dept_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, Department, dept_id, user, "department:read", perms)
    return DepartmentOut.model_validate(target, from_attributes=True)


@router.post(
    "/departments",
    response_model=DepartmentOut,
    status_code=201,
    dependencies=[Depends(require_perm("department:create")), Depends(bind_audit_context)],
)
async def create_department_endpoint(
    payload: DepartmentCreateIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    created = await create_department(db, payload)
    await db.commit()
    await db.refresh(created)
    return DepartmentOut.model_validate(created, from_attributes=True)


@router.patch(
    "/departments/{dept_id}",
    response_model=DepartmentOut,
    dependencies=[Depends(require_perm("department:update")), Depends(bind_audit_context)],
)
async def update_department_endpoint(
    dept_id: uuid.UUID,
    payload: DepartmentUpdateIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, Department, dept_id, user, "department:update", perms)
    updated = await update_department(db, target, payload)
    await db.commit()
    await db.refresh(updated)
    return DepartmentOut.model_validate(updated, from_attributes=True)


@router.post(
    "/departments/{dept_id}/move",
    response_model=DepartmentOut,
    dependencies=[Depends(require_perm("department:move")), Depends(bind_audit_context)],
)
async def move_department_endpoint(
    dept_id: uuid.UUID,
    payload: DepartmentMoveIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, Department, dept_id, user, "department:move", perms)
    try:
        await DepartmentService().move_department(
            db, target, new_parent_id=payload.new_parent_id, actor=user
        )
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    await db.refresh(target)
    return DepartmentOut.model_validate(target, from_attributes=True)


@router.delete(
    "/departments/{dept_id}",
    status_code=204,
    dependencies=[Depends(require_perm("department:delete")), Depends(bind_audit_context)],
)
async def delete_department_endpoint(
    dept_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Response:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, Department, dept_id, user, "department:delete", perms)
    try:
        await soft_delete_department(db, target, actor=user)
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    return Response(status_code=204)
