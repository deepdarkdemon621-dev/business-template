import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import ProblemDetails
from app.modules.auth.service import AuthService, _sign_jti


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


@pytest.mark.asyncio
async def test_refresh_success(svc, db, redis):
    jti = uuid.uuid4()
    session_obj = MagicMock(
        id=jti,
        user_id=uuid.uuid4(),
        device_label="Chrome",
        ip_address="1.2.3.4",
        last_used_at=datetime.now(tz=UTC),
        expires_at=datetime.now(tz=UTC) + timedelta(days=7),
    )
    session_obj.user = MagicMock(department_id=None)
    redis.exists.return_value = 0
    new_session = MagicMock(
        id=uuid.uuid4(),
        expires_at=datetime.now(tz=UTC) + timedelta(days=7),
    )
    with patch("app.modules.auth.service.crud") as mock_crud:
        mock_crud.get_session_by_id = AsyncMock(return_value=session_obj)
        mock_crud.create_session = AsyncMock(return_value=new_session)
        mock_crud.delete_session = AsyncMock()
        result = await svc.refresh(db=db, redis=redis, jti=str(jti), signed=_sign_jti(str(jti)))
    assert "access_token" in result


@pytest.mark.asyncio
async def test_refresh_denylisted(svc, db, redis):
    redis.exists.return_value = 1
    with pytest.raises(ProblemDetails) as ei:
        await svc.refresh(db=db, redis=redis, jti="some-jti", signed="sig")
    assert ei.value.code == "auth.invalid-token"


@pytest.mark.asyncio
async def test_logout(svc, db, redis):
    jti = uuid.uuid4()
    session_obj = MagicMock(id=jti, expires_at=datetime.now(tz=UTC) + timedelta(days=5))
    with patch("app.modules.auth.service.crud") as mock_crud:
        mock_crud.get_session_by_id = AsyncMock(return_value=session_obj)
        mock_crud.delete_session = AsyncMock()
        await svc.logout(db=db, redis=redis, jti=str(jti))
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_success(svc, db):
    user = MagicMock(password_hash="$argon2id$...")
    with (
        patch("app.modules.auth.service.verify_password", return_value=True),
        patch("app.modules.auth.service.hash_password", return_value="new-hash"),
        patch("app.modules.auth.service.crud") as mock_crud,
    ):
        mock_crud.update_user_password = AsyncMock()
        await svc.change_password(
            db=db, user=user, current_password="old", new_password="NewPass1234"
        )
    mock_crud.update_user_password.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_wrong_current(svc, db):
    user = MagicMock(password_hash="$argon2id$...")
    with patch("app.modules.auth.service.verify_password", return_value=False):
        with pytest.raises(ProblemDetails) as ei:
            await svc.change_password(db=db, user=user, current_password="wrong", new_password="x")
    assert ei.value.code == "auth.invalid-credentials"


@pytest.mark.asyncio
async def test_request_password_reset(svc, db, redis):
    user = MagicMock(id=uuid.uuid4())
    with (
        patch("app.modules.auth.service.crud") as mock_crud,
        patch("app.modules.auth.service.send_email") as mock_email,
    ):
        mock_crud.get_user_by_email = AsyncMock(return_value=user)
        await svc.request_password_reset(db=db, redis=redis, email="a@b.com")
    redis.set.assert_awaited_once()
    mock_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_password_reset_unknown_email(svc, db, redis):
    with patch("app.modules.auth.service.crud") as mock_crud:
        mock_crud.get_user_by_email = AsyncMock(return_value=None)
        await svc.request_password_reset(db=db, redis=redis, email="missing@b.com")
    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_password_reset(svc, db, redis):
    user_id = str(uuid.uuid4())
    redis.get.return_value = user_id
    user = MagicMock(id=user_id)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    db.execute.return_value = result_mock
    with (
        patch("app.modules.auth.service.hash_password", return_value="new-hash"),
        patch("app.modules.auth.service.crud") as mock_crud,
    ):
        mock_crud.update_user_password = AsyncMock()
        mock_crud.delete_user_sessions = AsyncMock(return_value=[])
        await svc.confirm_password_reset(
            db=db, redis=redis, token="reset-tok", new_password="NewPass1234"
        )
    mock_crud.update_user_password.assert_awaited_once()
    redis.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_password_reset_invalid_token(svc, db, redis):
    redis.get.return_value = None
    with pytest.raises(ProblemDetails) as ei:
        await svc.confirm_password_reset(db=db, redis=redis, token="bad-tok", new_password="x")
    assert ei.value.code == "auth.reset-token-invalid"


@pytest.mark.asyncio
async def test_list_sessions(svc, db):
    sessions = [MagicMock(id=uuid.uuid4()), MagicMock(id=uuid.uuid4())]
    with patch("app.modules.auth.service.crud") as mock_crud:
        mock_crud.get_user_sessions = AsyncMock(return_value=sessions)
        result = await svc.list_sessions(db=db, user_id=uuid.uuid4())
    assert len(result) == 2


@pytest.mark.asyncio
async def test_revoke_session(svc, db, redis):
    jti = uuid.uuid4()
    session_obj = MagicMock(id=jti, expires_at=datetime.now(tz=UTC) + timedelta(days=3))
    with patch("app.modules.auth.service.crud") as mock_crud:
        mock_crud.get_session_by_id = AsyncMock(return_value=session_obj)
        mock_crud.delete_session = AsyncMock()
        await svc.revoke_session(db=db, redis=redis, jti=jti, current_jti=uuid.uuid4())
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_own_session_rejected(svc, db, redis):
    jti = uuid.uuid4()
    with pytest.raises(ProblemDetails) as ei:
        await svc.revoke_session(db=db, redis=redis, jti=jti, current_jti=jti)
    assert ei.value.code == "auth.cannot-revoke-current"
