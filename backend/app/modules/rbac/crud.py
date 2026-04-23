from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rbac.models import Department, Permission, Role, RolePermission, UserRole
from app.modules.rbac.schemas import RoleCreateIn, RolePermissionItem


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


async def create_role(
    session: AsyncSession,
    payload: RoleCreateIn,
) -> Role:
    role = Role(code=payload.code, name=payload.name, is_builtin=False, is_superadmin=False)
    session.add(role)
    await session.flush()  # assign role.id
    if payload.permissions:
        await _insert_role_permissions(session, role.id, payload.permissions)
    return role


async def _insert_role_permissions(
    session: AsyncSession,
    role_id: uuid.UUID,
    items: list[RolePermissionItem],
) -> None:
    if not items:
        return
    codes = [i.permission_code for i in items]
    code_to_id = dict(
        (
            await session.execute(
                select(Permission.code, Permission.id).where(Permission.code.in_(codes))
            )
        ).all()
    )
    missing = [c for c in codes if c not in code_to_id]
    if missing:
        raise ValueError(f"Unknown permission codes: {missing}")

    session.add_all(
        [
            RolePermission(
                role_id=role_id,
                permission_id=code_to_id[item.permission_code],
                scope=item.scope.value,
            )
            for item in items
        ]
    )


async def get_role_with_permissions(
    session: AsyncSession,
    role_id: uuid.UUID,
) -> tuple[Role, list[RolePermissionItem]]:
    role = await session.get(Role, role_id)
    if role is None:
        raise LookupError(f"Role {role_id} not found.")
    rows = (
        await session.execute(
            select(Permission.code, RolePermission.scope)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.code)
        )
    ).all()
    items = [RolePermissionItem(permission_code=code, scope=scope) for code, scope in rows]
    return role, items


async def count_role_users(session: AsyncSession, role_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
    return int((await session.execute(stmt)).scalar_one())


async def count_role_permissions(session: AsyncSession, role_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(RolePermission)
        .where(RolePermission.role_id == role_id)
    )
    return int((await session.execute(stmt)).scalar_one())


async def delete_role(session: AsyncSession, role: Role) -> int:
    """Delete role; returns count of cascaded user_roles before deletion.

    DB-level ON DELETE CASCADE removes role_permissions + user_roles.
    """
    user_count = await count_role_users(session, role.id)
    await session.delete(role)
    await session.flush()
    return user_count


async def list_roles_with_counts(
    session: AsyncSession,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    user_count_sub = (
        select(UserRole.role_id, func.count().label("uc"))
        .group_by(UserRole.role_id)
        .subquery()
    )
    perm_count_sub = (
        select(RolePermission.role_id, func.count().label("pc"))
        .group_by(RolePermission.role_id)
        .subquery()
    )
    stmt = (
        select(Role, user_count_sub.c.uc, perm_count_sub.c.pc)
        .outerjoin(user_count_sub, user_count_sub.c.role_id == Role.id)
        .outerjoin(perm_count_sub, perm_count_sub.c.role_id == Role.id)
        .order_by(Role.name)
    )
    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)
    rows = (await session.execute(stmt)).all()
    return [
        {"role": role, "user_count": int(uc or 0), "permission_count": int(pc or 0)}
        for role, uc, pc in rows
    ]


async def list_all_permissions(session: AsyncSession) -> list[Permission]:
    stmt = select(Permission).order_by(Permission.resource, Permission.action)
    return list((await session.execute(stmt)).scalars().all())


async def replace_role_permissions(
    session: AsyncSession,
    role_id: uuid.UUID,
    items: list[RolePermissionItem],
) -> dict[str, list[str]]:
    """Replace the role's permission set atomically; return a diff summary."""
    current_rows = (
        await session.execute(
            select(Permission.code, RolePermission.scope, RolePermission.permission_id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
    ).all()
    current = {code: (scope, pid) for code, scope, pid in current_rows}

    desired = {i.permission_code: i.scope.value for i in items}

    added = sorted(set(desired) - set(current))
    removed = sorted(set(current) - set(desired))
    scope_changed = sorted(
        c for c in (set(desired) & set(current)) if desired[c] != current[c][0]
    )

    # Delete removed.
    for code in removed:
        _, pid = current[code]
        await session.execute(
            RolePermission.__table__.delete().where(
                (RolePermission.role_id == role_id)
                & (RolePermission.permission_id == pid)
            )
        )

    # Update scope_changed.
    for code in scope_changed:
        _, pid = current[code]
        await session.execute(
            RolePermission.__table__.update()
            .where(
                (RolePermission.role_id == role_id)
                & (RolePermission.permission_id == pid)
            )
            .values(scope=desired[code])
        )

    # Insert added — reuse _insert_role_permissions for code resolution + errors.
    new_items = [i for i in items if i.permission_code in added]
    if new_items:
        await _insert_role_permissions(session, role_id, new_items)

    await session.flush()
    return {"added": added, "removed": removed, "scope_changed": scope_changed}


