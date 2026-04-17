from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import FieldError, GuardViolationCtx, ProblemDetails, install_handlers


def _make_app() -> TestClient:
    app = FastAPI()
    install_handlers(app)

    @app.get("/not-found")
    def _nf():
        raise ProblemDetails(code="user.not-found", status=404, detail="User not found.")

    @app.get("/validation")
    def _v():
        raise ProblemDetails(
            code="user.invalid-email",
            status=422,
            detail="Validation failed.",
            errors=[FieldError(field="email", code="format", message="bad email")],
        )

    @app.get("/guard")
    def _g():
        raise ProblemDetails(
            code="department.has-users",
            status=409,
            detail="cannot delete",
            guard_violation=GuardViolationCtx(guard="NoDependents", params={"relation": "users"}),
        )

    return TestClient(app)


def test_problem_details_serialization_basic():
    r = _make_app().get("/not-found")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "User not found.",
        "code": "user.not-found",
    }


def test_problem_details_with_field_errors():
    body = _make_app().get("/validation").json()
    assert body["code"] == "user.invalid-email"
    assert body["errors"] == [{"field": "email", "code": "format", "message": "bad email"}]


def test_problem_details_with_guard_violation():
    body = _make_app().get("/guard").json()
    assert body["guardViolation"] == {"guard": "NoDependents", "params": {"relation": "users"}}
