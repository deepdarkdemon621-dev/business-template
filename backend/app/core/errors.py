from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.schemas import BaseSchema


class FieldError(BaseSchema):
    field: str
    code: str
    message: str | None = None


class GuardViolationCtx(BaseSchema):
    guard: str
    params: dict[str, Any] = {}


class ProblemDetails(Exception):
    def __init__(
        self,
        *,
        code: str,
        status: int,
        detail: str,
        title: str | None = None,
        type: str = "about:blank",
        errors: list[FieldError] | None = None,
        guard_violation: GuardViolationCtx | None = None,
    ) -> None:
        self.code = code
        self.status = status
        self.detail = detail
        self.title = title or HTTPStatus(status).phrase
        self.type = type
        self.errors = errors
        self.guard_violation = guard_violation
        super().__init__(detail)

    def to_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "code": self.code,
        }
        if self.errors is not None:
            body["errors"] = [e.model_dump(by_alias=True, mode="json") for e in self.errors]
        if self.guard_violation is not None:
            body["guardViolation"] = self.guard_violation.model_dump(by_alias=True, mode="json")
        return body


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemDetails)
    async def _pd_handler(_req: Request, exc: ProblemDetails) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=exc.to_body(),
            media_type="application/problem+json",
        )
