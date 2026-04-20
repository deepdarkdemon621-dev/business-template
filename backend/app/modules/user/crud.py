from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole


def build_list_users_stmt(is_active: bool | None = True) -> Select[tuple[User]]:
    stmt = select(User).order_by(User.created_at.desc())
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    return stmt


async def get_user_with_roles(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[User | None, list[Role]]:
    u = await session.get(User, user_id)
    if u is None:
        return None, []
    role_stmt = (
        select(Role).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    )
    roles = list((await session.execute(role_stmt)).scalars().all())
    return u, roles
