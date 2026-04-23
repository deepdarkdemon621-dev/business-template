from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guards import GuardViolationError
from app.modules.rbac.models import Department, Role, UserRole


class LastOfKind:
    """Forbid removing role `role_code` from the sole remaining holder.

    Expects `role_code` in kwargs; no-ops when it doesn't match the configured role.
    Bypassed for superadmins.
    """

    def __init__(self, role_code: str) -> None:
        self.role_code = role_code

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        role_code: str | None = None,
        **_: Any,
    ) -> None:
        if role_code != self.role_code:
            return
        if actor is not None and getattr(actor, "is_superadmin", False):
            return

        stmt = (
            select(func.count())
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code == self.role_code)
        )
        total = (await session.execute(stmt)).scalar_one()
        if total <= 1:
            raise GuardViolationError(
                code="last-of-kind",
                ctx={"role_code": self.role_code, "remaining": int(total)},
            )


class HasChildren:
    """Forbid delete when the department has any active children."""

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        **_: Any,
    ) -> None:
        stmt = (
            select(func.count())
            .select_from(Department)
            .where(Department.parent_id == instance.id)
            .where(Department.is_active.is_(True))
        )
        count = (await session.execute(stmt)).scalar_one()
        if count > 0:
            raise GuardViolationError(
                code="department.has-children",
                ctx={"department_id": str(instance.id), "active_children": int(count)},
            )


class HasAssignedUsers:
    """Forbid delete when any active user has this as their department_id."""

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        **_: Any,
    ) -> None:
        # Import inside to avoid a models ↔ guards cycle at import time.
        from app.modules.auth.models import User

        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.department_id == instance.id)
            .where(User.is_active.is_(True))
        )
        count = (await session.execute(stmt)).scalar_one()
        if count > 0:
            raise GuardViolationError(
                code="department.has-users",
                ctx={"department_id": str(instance.id), "assigned_users": int(count)},
            )


class NoCycle:
    """Forbid move when `new_parent_id` is self or a descendant of instance."""

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        new_parent_id: Any | None = None,
        **_: Any,
    ) -> None:
        if new_parent_id is None:
            return
        if new_parent_id == instance.id:
            raise GuardViolationError(
                code="department.self-parent",
                ctx={"department_id": str(instance.id)},
            )
        # Is new_parent_id inside the subtree of instance?
        # Subtree members have path starting with instance.path.
        target_path_stmt = select(Department.path).where(Department.id == new_parent_id)
        target_path = (await session.execute(target_path_stmt)).scalar_one_or_none()
        if target_path is None:
            return  # parent not found — let service/load_in_scope handle.
        if target_path.startswith(instance.path):
            raise GuardViolationError(
                code="department.cycle-detected",
                ctx={
                    "department_id": str(instance.id),
                    "new_parent_id": str(new_parent_id),
                },
            )


class SuperadminRoleLocked:
    """Refuse any mutation on the role flagged is_superadmin=True."""

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        **_: Any,
    ) -> None:
        if getattr(instance, "is_superadmin", False):
            raise GuardViolationError(
                code="role.superadmin-locked",
                ctx={"role_id": str(instance.id), "role_code": instance.code},
            )


class BuiltinRoleLocked:
    """Refuse name/code edits and delete on is_builtin=True roles.

    Matrix (`permissions`) edits are allowed — tenants can tune what
    builtin roles do, but not rename or remove them.

    Caller passes `changing={"name","code","permissions",...}` for updates;
    omit `changing` entirely to signal a delete attempt.
    """

    _IMMUTABLE_FIELDS = frozenset({"code", "name"})

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        changing: set[str] | None = None,
        **_: Any,
    ) -> None:
        if not getattr(instance, "is_builtin", False):
            return
        # Delete signalled by absence of `changing`.
        if changing is None:
            raise GuardViolationError(
                code="role.builtin-locked",
                ctx={"role_id": str(instance.id), "operation": "delete"},
            )
        forbidden = self._IMMUTABLE_FIELDS & changing
        if forbidden:
            raise GuardViolationError(
                code="role.builtin-locked",
                ctx={
                    "role_id": str(instance.id),
                    "operation": "update",
                    "immutable_fields": sorted(forbidden),
                },
            )


# Wire Department.__guards__ here (not at the bottom of rbac/models.py)
# because models.py is imported mid-load by guards.py's top-level
# `from app.modules.rbac.models import Department, ...`. At the bottom of
# models.py, this file is still initialising and the guard classes below
# do not yet exist, so a partial-import error fires. By the time we reach
# this point, both modules are fully loaded.
Department.__guards__ = {
    "delete": [HasChildren(), HasAssignedUsers()],
    "move": [NoCycle()],
}

Role.__guards__ = {
    "update": [SuperadminRoleLocked(), BuiltinRoleLocked()],
    "delete": [SuperadminRoleLocked(), BuiltinRoleLocked()],
}
