from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.errors import ProblemDetails
from app.modules.auth.models import User
from app.modules.rbac.constants import SUPERADMIN_ALL, ScopeEnum, widest
from app.modules.rbac.models import Department, Permission, Role, RolePermission, UserRole

__all__ = [
    "PermissionMap",
    "SUPERADMIN_ALL",
    "public_endpoint",
    "current_user_dep",
    "get_user_permissions",
    "load_permissions",
    "require_perm",
    "apply_scope",
    "load_in_scope",
]


async def current_user_dep(
    authorization: Annotated[str, Header()] = "",
    session: AsyncSession = Depends(get_session),
) -> User:
    """FastAPI dependency wrapper around core.auth.get_current_user.

    `get_current_user` takes plain (authorization, session) args; this wrapper
    wires them up to FastAPI's Header + Depends system so routes can use it
    directly via `Depends(current_user_dep)`.
    """
    return await get_current_user(authorization, session)


PermissionMap = dict[str, ScopeEnum] | object


async def public_endpoint() -> None:
    """No-op dependency that marks a route as intentionally public (no auth required)."""


async def get_user_permissions(db: AsyncSession, user: User) -> PermissionMap:
    """Return {code: widest_scope} for user, or SUPERADMIN_ALL sentinel."""
    result = await db.execute(
        select(Role.is_superadmin)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
        .where(Role.is_superadmin.is_(True))
        .limit(1)
    )
    if result.first() is not None:
        return SUPERADMIN_ALL

    stmt = (
        select(Permission.code, RolePermission.scope)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id)
    )
    rows = await db.execute(stmt)
    out: dict[str, ScopeEnum] = {}
    for code, scope_str in rows:
        scope = ScopeEnum(scope_str)
        out[code] = widest(out[code], scope) if code in out else scope
    return out


async def load_permissions(
    request: Request,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> PermissionMap:
    """Per-request permission load; cached on request.state for request duration."""
    if not hasattr(request.state, "permissions"):
        request.state.permissions = await get_user_permissions(db, user)
    return request.state.permissions


def require_perm(code: str):
    """Dependency factory. Raises 403 if user lacks `code` at any scope.

    Superadmin bypasses. Does NOT check scope — caller uses apply_scope/load_in_scope.
    """

    async def _dep(perms: PermissionMap = Depends(load_permissions)) -> None:
        if perms is SUPERADMIN_ALL:
            return
        assert isinstance(perms, dict)
        if code not in perms:
            raise ProblemDetails(
                code="permission.denied",
                status=403,
                detail=f"Permission '{code}' required.",
            )

    return _dep


def apply_scope(
    stmt: Select,
    user: User,
    code: str,
    model: type,
    perms: PermissionMap,
) -> Select:
    """Add WHERE clause narrowing stmt to rows user can see for code."""
    if perms is SUPERADMIN_ALL:
        return stmt
    assert isinstance(perms, dict)
    scope = perms.get(code)
    if scope is None:
        # No permission at all -- return empty result
        return stmt.where(False)
    if scope == ScopeEnum.GLOBAL:
        return stmt
    if not hasattr(model, "__scope_map__"):
        raise RuntimeError(f"Model {model.__name__} has no __scope_map__ -- cannot apply_scope")
    field_name = model.__scope_map__[scope]
    field = getattr(model, field_name)

    if scope == ScopeEnum.OWN:
        return stmt.where(field == user.id)
    if scope == ScopeEnum.DEPT:
        # Union of per-assignment scope_values (or user.department_id fallback)
        # for every role this user holds that grants `code` at DEPT scope.
        dept_ids = (
            select(func.coalesce(UserRole.scope_value, user.department_id))
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(UserRole.user_id == user.id)
            .where(Permission.code == code)
            .where(RolePermission.scope == ScopeEnum.DEPT.value)
        )
        return stmt.where(field.in_(dept_ids))
    if scope == ScopeEnum.DEPT_TREE:
        # For each role/permission granting this code at dept_tree scope,
        # expand the anchor dept (scope_value or user.department_id) to its
        # subtree via Department.path LIKE prefix.
        anchor_ids = (
            select(func.coalesce(UserRole.scope_value, user.department_id).label("anchor"))
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(UserRole.user_id == user.id)
            .where(Permission.code == code)
            .where(RolePermission.scope == ScopeEnum.DEPT_TREE.value)
        ).subquery("anchor")
        anchor_paths = (
            select(Department.path)
            .where(Department.id.in_(select(anchor_ids.c.anchor)))
            .subquery("anchor_paths")
        )
        subtree = (
            select(Department.id)
            .join(
                anchor_paths,
                Department.path.like(func.concat(anchor_paths.c.path, "%")),
            )
        )
        return stmt.where(field.in_(subtree))
    raise RuntimeError(f"Unknown scope: {scope}")


async def load_in_scope(
    db: AsyncSession,
    model: type,
    row_id,
    user: User,
    code: str,
    perms: PermissionMap,
):
    """Fetch row by id, enforcing scope.

    Raises 404 (not 403) on out-of-scope to avoid leaking existence.
    """
    stmt = select(model).where(model.id == row_id)
    stmt = apply_scope(stmt, user, code, model, perms)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise ProblemDetails(
            code="resource.not-found",
            status=404,
            detail="Resource not found or not in scope.",
        )
    return row
