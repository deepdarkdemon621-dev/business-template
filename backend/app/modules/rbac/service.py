"""RBAC service layer.

Business operations on Role: create / update / delete + matrix diff.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import FieldError, ProblemDetails
from app.core.guards import GuardViolationError
from app.modules.audit.service import _diff_dict, _role_snapshot, audit
from app.modules.rbac import crud
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import (
    RoleCreateIn,
    RoleUpdateIn,
)


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

        await audit.role_created(session, role)
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

        before_snap = _role_snapshot(role)

        if payload.code is not None and payload.code != role.code:
            role.code = payload.code
        if payload.name is not None and payload.name != role.name:
            role.name = payload.name

        matrix_diff: dict[str, list[dict[str, str]]] | None = None
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

        after_snap = _role_snapshot(role)
        field_changes = _diff_dict(before_snap, after_snap)
        if field_changes:
            await audit.role_updated(session, role, changes=field_changes)

        if matrix_diff and (matrix_diff["added"] or matrix_diff["removed"] or matrix_diff["scope_changed"]):
            await audit.role_permissions_updated(
                session,
                role,
                added=matrix_diff["added"],
                removed=matrix_diff["removed"],
                scope_changed=matrix_diff["scope_changed"],
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
        snap = _role_snapshot(role)
        deleted_user_roles = await crud.delete_role(session, role)
        await audit.role_deleted(session, snap, role_id=role_id, code=role_code)
        return deleted_user_roles
