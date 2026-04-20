from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.modules.auth.models import User
from app.modules.rbac.constants import SUPERADMIN_ALL, ScopeEnum, widest
from app.modules.rbac.models import Department, Permission, Role, RolePermission, UserRole

__all__ = [
    "PermissionMap",
    "SUPERADMIN_ALL",
    "public_endpoint",
    "get_user_permissions",
    "load_permissions",
    "require_perm",
    "apply_scope",
    "load_in_scope",
]

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
    user: User = Depends(get_current_user),
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"type": "permission_denied", "missing": code},
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
        raise RuntimeError(
            f"Model {model.__name__} has no __scope_map__ -- cannot apply_scope"
        )
    field_name = model.__scope_map__[scope]
    field = getattr(model, field_name)

    if scope == ScopeEnum.OWN:
        return stmt.where(field == user.id)
    if scope == ScopeEnum.DEPT:
        return stmt.where(field == user.department_id)
    if scope == ScopeEnum.DEPT_TREE:
        # SQL-level: find user's dept path, then select all dept ids whose path
        # starts with user_path, then filter rows by that subtree.
        user_path = (
            select(Department.path)
            .where(Department.id == user.department_id)
            .scalar_subquery()
        )
        subtree = select(Department.id).where(
            Department.path.like(func.concat(user_path, "%"))
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
        raise HTTPException(status_code=404, detail={"type": "not_found"})
    return row
