"""RBAC service layer.

Business operations on Role: create / update / delete + matrix diff.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import FieldError, ProblemDetails
from app.core.guards import GuardViolationError
from app.modules.rbac import crud
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import (
    RoleCreateIn,
    RoleUpdateIn,
)

logger = logging.getLogger(__name__)


def _guard_to_problem(e: GuardViolationError) -> ProblemDetails:
    # Role guards map to 409 (conflict with immutable state).
    return ProblemDetails(
        code=e.code,
        status=409,
        detail=f"Operation blocked by guard: {e.code}.",
    )


class RoleService:
    """Business operations on Role: create / update / delete + matrix diff."""

    async def create(
        self,
        session: AsyncSession,
        payload: RoleCreateIn,
    ) -> Role:
        try:
            role = await crud.create_role(session, payload)
            await session.flush()
        except ValueError as e:
            # Raised by _insert_role_permissions for unknown permission codes.
            raise ProblemDetails(
                code="role.permission-unknown",
                status=422,
                detail=str(e),
                errors=[
                    FieldError(
                        field="permissions",
                        code="unknown-code",
                        message=str(e),
                    )
                ],
            ) from e
        except IntegrityError as e:
            # Unique constraint on roles.code.
            raise ProblemDetails(
                code="role.code-conflict",
                status=409,
                detail=f"Role code '{payload.code}' already exists.",
            ) from e

        logger.info(
            "role.created",
            extra={
                "role_id": str(role.id),
                "code": role.code,
                "name": role.name,
                "permissions": [
                    {"code": p.permission_code, "scope": p.scope.value}
                    for p in payload.permissions
                ],
            },
        )
        return role

    async def update(
        self,
        session: AsyncSession,
        role: Role,
        payload: RoleUpdateIn,
    ) -> Role:
        changing = self._compute_changing(payload)
        # Guards — iterate in list order (SuperadminRoleLocked first, then BuiltinRoleLocked).
        for guard in Role.__guards__.get("update", []):
            try:
                await guard.check(session, role, changing=changing)
            except GuardViolationError as e:
                raise _guard_to_problem(e) from e

        metadata_changes: dict[str, Any] = {}
        if payload.code is not None and payload.code != role.code:
            role.code = payload.code
            metadata_changes["code"] = payload.code
        if payload.name is not None and payload.name != role.name:
            role.name = payload.name
            metadata_changes["name"] = payload.name

        matrix_diff: dict[str, list[str]] | None = None
        if payload.permissions is not None:
            try:
                matrix_diff = await crud.replace_role_permissions(
                    session, role.id, payload.permissions
                )
            except ValueError as e:
                raise ProblemDetails(
                    code="role.permission-unknown",
                    status=422,
                    detail=str(e),
                    errors=[
                        FieldError(
                            field="permissions",
                            code="unknown-code",
                            message=str(e),
                        )
                    ],
                ) from e

        try:
            await session.flush()
        except IntegrityError as e:
            raise ProblemDetails(
                code="role.code-conflict",
                status=409,
                detail=f"Role code '{payload.code}' already exists.",
            ) from e

        if metadata_changes or (matrix_diff and any(matrix_diff.values())):
            logger.info(
                "role.updated",
                extra={
                    "role_id": str(role.id),
                    "metadata_changes": metadata_changes,
                    "matrix_diff": matrix_diff,
                },
            )
        return role

    @staticmethod
    def _compute_changing(payload: RoleUpdateIn) -> set[str]:
        changing: set[str] = set()
        if payload.code is not None:
            changing.add("code")
        if payload.name is not None:
            changing.add("name")
        if payload.permissions is not None:
            changing.add("permissions")
        return changing

    async def delete(
        self,
        session: AsyncSession,
        role: Role,
    ) -> int:
        # Guards — `changing` is omitted to signal delete intent.
        for guard in Role.__guards__.get("delete", []):
            try:
                await guard.check(session, role)
            except GuardViolationError as e:
                raise _guard_to_problem(e) from e

        role_code = role.code
        role_id = role.id
        deleted_user_roles = await crud.delete_role(session, role)

        logger.info(
            "role.deleted",
            extra={
                "role_id": str(role_id),
                "code": role_code,
                "deleted_user_roles": deleted_user_roles,
            },
        )
        return deleted_user_roles
