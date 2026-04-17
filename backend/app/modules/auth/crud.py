from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User, UserSession


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    device_label: str | None,
    ip_address: str | None,
    ttl_days: int,
) -> UserSession:
    now = datetime.now(tz=UTC)
    user_session = UserSession(
        id=uuid.uuid4(),
        user_id=user_id,
        device_label=device_label,
        ip_address=ip_address,
        last_used_at=now,
        expires_at=now + timedelta(days=ttl_days),
    )
    session.add(user_session)
    await session.flush()
    return user_session


async def get_session_by_id(session: AsyncSession, jti: uuid.UUID) -> UserSession | None:
    result = await session.execute(select(UserSession).where(UserSession.id == jti))
    return result.scalar_one_or_none()


async def get_user_sessions(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[UserSession]:
    result = await session.execute(
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .order_by(UserSession.last_used_at.desc())
    )
    return list(result.scalars().all())


async def delete_session(session: AsyncSession, jti: uuid.UUID) -> None:
    await session.execute(delete(UserSession).where(UserSession.id == jti))
    await session.flush()


async def delete_user_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[UserSession]:
    result = await session.execute(
        select(UserSession).where(UserSession.user_id == user_id)
    )
    sessions = list(result.scalars().all())
    if sessions:
        await session.execute(delete(UserSession).where(UserSession.user_id == user_id))
        await session.flush()
    return sessions


async def update_user_password(
    session: AsyncSession,
    user: Any,
    password_hash: str,
) -> None:
    user.password_hash = password_hash
    user.must_change_password = False
    await session.flush()
