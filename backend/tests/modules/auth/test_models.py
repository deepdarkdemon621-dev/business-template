from sqlalchemy import inspect

from app.modules.auth.models import User, UserSession


def test_user_table_name():
    assert User.__tablename__ == "users"


def test_user_has_expected_columns():
    cols = {c.name for c in inspect(User).columns}
    expected = {
        "id",
        "email",
        "password_hash",
        "full_name",
        "department_id",
        "is_active",
        "must_change_password",
        "created_at",
        "updated_at",
    }
    assert expected <= cols


def test_user_session_table_name():
    assert UserSession.__tablename__ == "user_sessions"


def test_user_session_has_expected_columns():
    cols = {c.name for c in inspect(UserSession).columns}
    expected = {
        "id",
        "user_id",
        "device_label",
        "ip_address",
        "created_at",
        "last_used_at",
        "expires_at",
    }
    assert expected <= cols
