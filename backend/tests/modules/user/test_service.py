from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password, verify_password
from app.core.errors import ProblemDetails
from app.core.guards import GuardViolationError
from app.modules.auth.models import User
from app.modules.rbac.constants import SUPERADMIN_ROLE_CODE
from app.modules.rbac.models import Role, UserRole
from app.modules.user.schemas import UserCreateIn, UserUpdateIn
from app.modules.user.service import (
    assign_role,
    create_user,
    revoke_role,
    soft_delete_user,
    update_user,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def actor(db_session: AsyncSession) -> User:
    u = User(email="actor@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Actor")
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def superadmin_actor(db_session: AsyncSession) -> User:
    role = (
        await db_session.execute(select(Role).where(Role.code == SUPERADMIN_ROLE_CODE))
    ).scalar_one()
    u = User(email="sa@ex.com", password_hash=hash_password("pw-aaa111"), full_name="SA")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=role.id))
    await db_session.flush()
    return u


async def test_create_user_hashes_password_and_sets_flags(
    db_session: AsyncSession, actor: User
) -> None:
    payload = UserCreateIn(
        email="new@ex.com",
        password="GoodOne123",
        full_name="New",
    )
    u = await create_user(db_session, payload, actor=actor)
    assert u.email == "new@ex.com"
    assert u.password_hash != "GoodOne123"
    assert verify_password("GoodOne123", u.password_hash)
    assert u.must_change_password is True
    assert u.is_active is True


async def test_update_user_applies_partial(db_session: AsyncSession, actor: User) -> None:
    target = User(email="t@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Old Name")
    db_session.add(target)
    await db_session.flush()

    patch = UserUpdateIn(full_name="New Name")
    updated = await update_user(db_session, target, patch, actor=actor)
    assert updated.full_name == "New Name"


async def test_soft_delete_user_flips_is_active(db_session: AsyncSession, actor: User) -> None:
    target = User(email="t2@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T2")
    db_session.add(target)
    await db_session.flush()

    await soft_delete_user(db_session, target, actor=actor)
    await db_session.refresh(target)
    assert target.is_active is False


async def test_soft_delete_blocked_when_self(db_session: AsyncSession, actor: User) -> None:
    with pytest.raises(GuardViolationError) as ei:
        await soft_delete_user(db_session, actor, actor=actor)
    assert ei.value.code == "self-protection"


async def test_superadmin_can_self_delete(db_session: AsyncSession, superadmin_actor: User) -> None:
    await soft_delete_user(db_session, superadmin_actor, actor=superadmin_actor)
    await db_session.refresh(superadmin_actor)
    assert superadmin_actor.is_active is False


async def test_assign_role_is_idempotent(db_session: AsyncSession, actor: User) -> None:
    target = User(email="t3@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T3")
    role = Role(code="r", name="R")
    db_session.add_all([target, role])
    await db_session.flush()

    await assign_role(db_session, target, role, actor=actor)
    await assign_role(db_session, target, role, actor=actor)  # no error
    count = (
        await db_session.execute(
            select(func.count()).select_from(UserRole).where(UserRole.user_id == target.id)
        )
    ).scalar_one()
    assert count == 1


async def test_revoke_role_removes_row(db_session: AsyncSession, actor: User) -> None:
    target = User(email="t4@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T4")
    role = Role(code="rr", name="RR")
    db_session.add_all([target, role])
    await db_session.flush()
    db_session.add(UserRole(user_id=target.id, role_id=role.id))
    await db_session.flush()

    await revoke_role(db_session, target, role, actor=actor)
    count = (
        await db_session.execute(
            select(func.count()).select_from(UserRole).where(UserRole.user_id == target.id)
        )
    ).scalar_one()
    assert count == 0


async def test_revoke_role_raises_when_not_assigned(db_session: AsyncSession, actor: User) -> None:
    target = User(email="t5@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T5")
    role = Role(code="rrr", name="RRR")
    db_session.add_all([target, role])
    await db_session.flush()

    with pytest.raises(ProblemDetails) as ei:
        await revoke_role(db_session, target, role, actor=actor)
    assert ei.value.status == 404
