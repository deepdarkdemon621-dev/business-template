from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    UserRead,
)


def test_login_request_accepts_camel():
    req = LoginRequest.model_validate({"email": "a@b.com", "password": "x"})
    assert req.email == "a@b.com"


def test_login_response_serializes_camel():
    data = LoginResponse(
        access_token="tok",
        expires_in=1800,
        user=UserRead(
            id="00000000-0000-0000-0000-000000000001",
            email="a@b.com",
            full_name="Ada",
            department_id=None,
            is_active=True,
            must_change_password=False,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        ),
        must_change_password=False,
    )
    d = data.model_dump(by_alias=True, mode="json")
    assert "accessToken" in d
    assert "expiresIn" in d
    assert "mustChangePassword" in d


def test_password_change_must_match_rule():
    schema = PasswordChangeRequest.model_json_schema()
    x_rules = schema.get("x-rules", [])
    rule_names = [r["name"] for r in x_rules]
    assert "mustMatch" in rule_names


def test_password_reset_confirm_must_match_rule():
    schema = PasswordResetConfirmRequest.model_json_schema()
    x_rules = schema.get("x-rules", [])
    rule_names = [r["name"] for r in x_rules]
    assert "mustMatch" in rule_names
