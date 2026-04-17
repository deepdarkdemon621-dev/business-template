import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import ProblemDetails
from app.modules.auth.service import AuthService


@pytest.fixture
def svc():
    return AuthService()


@pytest.fixture
def db():
    return AsyncMock()


@pytest.fixture
def redis():
    return AsyncMock()


@pytest.mark.asyncio
async def test_login_success(svc, db, redis):
    redis.get.return_value = "0"
    user = MagicMock(
        id=uuid.uuid4(),
        email="a@b.com",
        password_hash="$argon2id$...",
        full_name="Ada",
        is_active=True,
        must_change_password=False,
        department_id=None,
    )
    with (
        patch("app.modules.auth.service.crud") as mock_crud,
        patch("app.modules.auth.service.verify_password", return_value=True),
        patch("app.modules.auth.service.verify_captcha", return_value=True),
        patch("app.modules.auth.service.clear_failed_logins") as mock_clear,
        patch("app.modules.auth.service.create_access_token", return_value="jwt-tok"),
    ):
        mock_crud.get_user_by_email = AsyncMock(return_value=user)
        session_obj = MagicMock(id=uuid.uuid4())
        mock_crud.create_session = AsyncMock(return_value=session_obj)
        result = await svc.login(
            db=db,
            redis=redis,
            email="a@b.com",
            password="secret",
            captcha=None,
            device_label="Chrome",
            ip_address="1.2.3.4",
        )
    assert result["access_token"] == "jwt-tok"
    assert result["user"] is user
    mock_clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_locked_out(svc, db, redis):
    redis.get.return_value = "5"
    with pytest.raises(ProblemDetails) as ei:
        await svc.login(
            db=db,
            redis=redis,
            email="a@b.com",
            password="x",
            captcha=None,
            device_label=None,
            ip_address=None,
        )
    assert ei.value.code == "auth.locked-out"


@pytest.mark.asyncio
async def test_login_bad_password(svc, db, redis):
    redis.get.return_value = "0"
    user = MagicMock(is_active=True)
    with (
        patch("app.modules.auth.service.crud") as mock_crud,
        patch("app.modules.auth.service.verify_password", return_value=False),
        patch("app.modules.auth.service.verify_captcha", return_value=True),
        patch("app.modules.auth.service.record_failed_login") as mock_record,
    ):
        mock_crud.get_user_by_email = AsyncMock(return_value=user)
        with pytest.raises(ProblemDetails) as ei:
            await svc.login(
                db=db,
                redis=redis,
                email="a@b.com",
                password="wrong",
                captcha=None,
                device_label=None,
                ip_address=None,
            )
    assert ei.value.code == "auth.invalid-credentials"
    mock_record.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_user_not_found(svc, db, redis):
    redis.get.return_value = "0"
    with (
        patch("app.modules.auth.service.crud") as mock_crud,
        patch("app.modules.auth.service.verify_captcha", return_value=True),
    ):
        mock_crud.get_user_by_email = AsyncMock(return_value=None)
        with pytest.raises(ProblemDetails) as ei:
            await svc.login(
                db=db,
                redis=redis,
                email="a@b.com",
                password="x",
                captcha=None,
                device_label=None,
                ip_address=None,
            )
    assert ei.value.code == "auth.invalid-credentials"
