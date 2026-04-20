from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guards import GuardViolationError
from app.modules.rbac.models import Role, UserRole


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
