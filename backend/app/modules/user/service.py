from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.errors import ProblemDetails
from app.modules.audit.service import _diff_dict, _user_snapshot, audit
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole
from app.modules.user.schemas import UserCreateIn, UserUpdateIn


async def _run_guards(
    session: AsyncSession, action: str, target: User, *, actor: User, **ctx
) -> None:
    guards = getattr(User, "__guards__", {}).get(action, [])
    for g in guards:
        await g.check(session, target, actor=actor, **ctx)


async def create_user(session: AsyncSession, payload: UserCreateIn, *, actor: User) -> User:
    u = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        department_id=payload.department_id,
        must_change_password=payload.must_change_password,
    )
    session.add(u)
    await session.flush()
    await audit.user_created(session, u)
    return u


async def update_user(
    session: AsyncSession, target: User, payload: UserUpdateIn, *, actor: User
) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "is_active" in data and data["is_active"] is False:
        await _run_guards(session, "deactivate", target, actor=actor)
    before = _user_snapshot(target)
    for k, v in data.items():
        setattr(target, k, v)
    await session.flush()
    after = _user_snapshot(target)
    changes = _diff_dict(before, after)
    if changes:
        await audit.user_updated(session, target, changes)
    return target


async def soft_delete_user(session: AsyncSession, target: User, *, actor: User) -> None:
    await _run_guards(session, "delete", target, actor=actor)
    snap = _user_snapshot(target)  # snapshot BEFORE state mutation (is_active still True)
    target.is_active = False
    await session.flush()
    await audit.user_deleted(session, snap, user_id=target.id, email=target.email)


async def assign_role(session: AsyncSession, target: User, role: Role, *, actor: User) -> None:
    existing = (
        await session.execute(
            select(UserRole).where(UserRole.user_id == target.id, UserRole.role_id == role.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return  # already assigned — no-op, no audit event
    session.add(UserRole(user_id=target.id, role_id=role.id, granted_by=actor.id))
    await session.flush()
    # scope="role": UserRole has no per-assignment scope; perm scopes live on RolePermission.
    await audit.user_role_assigned(session, target, role_code=role.code, scope="role")


async def revoke_role(session: AsyncSession, target: User, role: Role, *, actor: User) -> None:
    existing = (
        await session.execute(
            select(UserRole).where(UserRole.user_id == target.id, UserRole.role_id == role.id)
        )
    ).scalar_one_or_none()
    if existing is None:
        raise ProblemDetails(
            code="role-not-assigned",
            status=404,
            detail=f"Role '{role.code}' is not assigned to this user.",
        )

    await _run_guards(session, "strip_role", target, actor=actor, role_code=role.code)
    await session.execute(
        delete(UserRole).where(UserRole.user_id == target.id, UserRole.role_id == role.id)
    )
    await session.flush()
    # scope="role": UserRole has no per-assignment scope; perm scopes live on RolePermission.
    await audit.user_role_revoked(session, target, role_code=role.code, scope="role")
