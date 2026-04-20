from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole
from app.modules.user.crud import (
    build_list_users_stmt,
    get_user_with_roles,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession) -> tuple[User, Role]:
    u = User(email="u@ex.com", password_hash=hash_password("pw-aaa111"), full_name="U")
    r = Role(code="r1", name="R1")
    db_session.add_all([u, r])
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=r.id))
    await db_session.flush()
    return u, r


async def test_build_list_users_stmt_default_excludes_inactive(
    db_session: AsyncSession, seeded: tuple[User, Role]
) -> None:
    u, _ = seeded
    u.is_active = False
    active = User(
        email="active@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Active"
    )
    db_session.add(active)
    await db_session.flush()
    stmt = build_list_users_stmt(is_active=True)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert rows
    assert all(row.is_active for row in rows)
    assert u.id not in {r.id for r in rows}


async def test_build_list_users_stmt_none_shows_all(
    db_session: AsyncSession, seeded: tuple[User, Role]
) -> None:
    u, _ = seeded
    u.is_active = False
    active = User(email="active2@ex.com", password_hash=hash_password("pw-aaa111"), full_name="A2")
    db_session.add(active)
    await db_session.flush()
    stmt = build_list_users_stmt(is_active=None)
    rows = (await db_session.execute(stmt)).scalars().all()
    ids = {r.id for r in rows}
    assert u.id in ids
    assert active.id in ids


async def test_build_list_users_stmt_is_active_false_shows_only_inactive(
    db_session: AsyncSession, seeded: tuple[User, Role]
) -> None:
    u, _ = seeded
    u.is_active = False
    await db_session.flush()
    stmt = build_list_users_stmt(is_active=False)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert rows and all(not row.is_active for row in rows)


async def test_get_user_with_roles_returns_user_and_roles(
    db_session: AsyncSession, seeded: tuple[User, Role]
) -> None:
    u, r = seeded
    user, roles = await get_user_with_roles(db_session, u.id)
    assert user.id == u.id
    assert len(roles) == 1 and roles[0].id == r.id


async def test_get_user_with_roles_returns_none_when_missing(db_session: AsyncSession) -> None:
    import uuid

    user, roles = await get_user_with_roles(db_session, uuid.uuid4())
    assert user is None and roles == []
