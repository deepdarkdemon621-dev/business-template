from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rbac.models import Department, Role, UserRole


async def list_departments(db: AsyncSession):
    result = await db.execute(select(Department).order_by(Department.depth, Department.name))
    return result.scalars().all()


async def get_role_by_code(db: AsyncSession, code: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.code == code))
    return result.scalar_one_or_none()


async def grant_role(db: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
    """Returns True if a new row was inserted, False if already present."""
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    if result.first() is not None:
        return False
    db.add(UserRole(user_id=user_id, role_id=role_id))
    await db.flush()
    return True


async def revoke_role(db: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    await db.delete(row)
    await db.flush()
    return True
