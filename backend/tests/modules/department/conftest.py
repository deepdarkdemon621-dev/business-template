from __future__ import annotations

import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Department, Role, UserRole


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["accessToken"]


@pytest_asyncio.fixture
async def admin_client(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> AsyncClient:
    """AsyncClient authenticated as a superadmin; bypasses every permission."""
    user = User(
        email="admin_dept@ex.com",
        password_hash=hash_password("ValidPass123"),
        full_name="Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    sa_role = (
        await db_session.execute(select(Role).where(Role.code == "superadmin"))
    ).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=sa_role.id))
    await db_session.commit()

    token = await _login(client_with_db, "admin_dept@ex.com", "ValidPass123")
    client_with_db.headers["Authorization"] = f"Bearer {token}"
    return client_with_db


@pytest_asyncio.fixture
async def seed_department_tree(db_session: AsyncSession) -> dict[str, uuid.UUID]:
    root = Department(name="Root", path="/root/", depth=0)
    other_root = Department(name="Other", path="/other/", depth=0)
    db_session.add_all([root, other_root])
    await db_session.flush()
    leaf = Department(
        name="Leaf", parent_id=root.id, path="/root/leaf/", depth=1
    )
    db_session.add(leaf)
    await db_session.commit()
    return {
        "root_id": root.id,
        "other_root_id": other_root.id,
        "leaf_id": leaf.id,
    }
