import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import SUPERADMIN_ALL, get_user_permissions
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole


@pytest.mark.asyncio
async def test_get_user_permissions_superadmin_returns_sentinel(
    db_session: AsyncSession,
):
    user = User(
        id=uuid.uuid4(),
        email="s@example.com",
        full_name="S",
        password_hash="x",
        is_active=True,
    )
    db_session.add(user)
    superadmin_role = (
        await db_session.execute(select(Role).where(Role.code == "superadmin"))
    ).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=superadmin_role.id))
    await db_session.flush()

    result = await get_user_permissions(db_session, user)
    assert result is SUPERADMIN_ALL


@pytest.mark.asyncio
async def test_get_user_permissions_admin_role_returns_dict_with_global(
    db_session: AsyncSession,
):
    """Admin role grants all 15 codes at scope=global. Fold should yield dict[str, ScopeEnum]."""
    from app.modules.rbac.constants import ScopeEnum

    user = User(
        id=uuid.uuid4(),
        email="a@example.com",
        full_name="A",
        password_hash="x",
        is_active=True,
    )
    db_session.add(user)
    admin_role = (
        await db_session.execute(select(Role).where(Role.code == "admin"))
    ).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))
    await db_session.flush()

    result = await get_user_permissions(db_session, user)
    assert result is not SUPERADMIN_ALL
    assert isinstance(result, dict)
    assert len(result) == 15
    assert result["user:read"] == ScopeEnum.GLOBAL
