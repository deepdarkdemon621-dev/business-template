import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.auth.crud import (
    create_session,
    delete_session,
    delete_user_sessions,
    get_session_by_id,
    get_user_by_email,
    get_user_sessions,
    update_user_password,
)


@pytest.fixture
def session():
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_user_by_email(session):
    fake_user = MagicMock(email="a@b.com")
    result = MagicMock()
    result.scalar_one_or_none.return_value = fake_user
    session.execute.return_value = result
    user = await get_user_by_email(session, "a@b.com")
    assert user.email == "a@b.com"


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    user = await get_user_by_email(session, "missing@b.com")
    assert user is None


@pytest.mark.asyncio
async def test_create_session(session):
    now = datetime.now(tz=UTC)
    sess = await create_session(
        session,
        user_id=uuid.uuid4(),
        device_label="Chrome",
        ip_address="1.2.3.4",
        ttl_days=7,
    )
    assert sess.device_label == "Chrome"
    assert sess.ip_address == "1.2.3.4"
    assert sess.expires_at > now
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_password(session):
    user = MagicMock()
    await update_user_password(session, user, "new-hash")
    assert user.password_hash == "new-hash"
    assert user.must_change_password is False
    session.flush.assert_awaited_once()
