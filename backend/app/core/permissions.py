from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.modules.auth.models import User
from app.modules.rbac.constants import SUPERADMIN_ALL, ScopeEnum, widest
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole

__all__ = [
    "PermissionMap",
    "SUPERADMIN_ALL",
    "public_endpoint",
    "get_user_permissions",
    "load_permissions",
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
