from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole
from tests.modules.user.conftest import login


@pytest_asyncio.fixture
async def admin_token(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str]:
    """Admin user assigned the seeded 'admin' role (all seed perms at scope=global,
    including role:create/update/delete from migration 0006)."""
    admin_role = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()
    u = User(
        email="rbac-admin@ex.com",
        password_hash=hash_password("pw-aaa111"),
        full_name="RBAC Admin",
    )
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=admin_role.id))
    await db_session.commit()
    token = await login(client_with_db, "rbac-admin@ex.com", "pw-aaa111")
    return client_with_db, token


@pytest_asyncio.fixture
async def member_token(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str]:
    """Plain user with the built-in 'member' role (no role:* write perms)."""
    member_role = (
        await db_session.execute(select(Role).where(Role.code == "member"))
    ).scalar_one()
    u = User(
        email="rbac-member@ex.com",
        password_hash=hash_password("pw-aaa111"),
        full_name="RBAC Member",
    )
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=member_role.id))
    await db_session.commit()
    token = await login(client_with_db, "rbac-member@ex.com", "pw-aaa111")
    return client_with_db, token
