from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_ident(name: str) -> str:
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


class GuardViolationError(Exception):
    def __init__(self, *, code: str, ctx: dict[str, Any]) -> None:
        self.code = code
        self.ctx = ctx
        super().__init__(code)


@runtime_checkable
class Guard(Protocol):
    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        **kwargs: Any,
    ) -> None: ...


class NoDependents:
    def __init__(self, relation: str, fk_col: str) -> None:
        self.relation = _validate_ident(relation)
        self.fk_col = _validate_ident(fk_col)

    async def check(
        self, session: AsyncSession, instance: Any, *, actor: Any | None = None, **_: Any
    ) -> None:
        stmt = (
            select(func.count())
            .select_from(text(self.relation))
            .where(text(f"{self.fk_col} = :pk"))
            .params(pk=instance.id)
        )
        count = (await session.execute(stmt)).scalar_one()
        if count > 0:
            raise GuardViolationError(
                code="has-dependents",
                ctx={"relation": self.relation, "fk_col": self.fk_col, "count": int(count)},
            )


class StateAllows:
    def __init__(self, field: str, allowed: list[Any]) -> None:
        self.field = field
        self.allowed = list(allowed)

    async def check(
        self, session: AsyncSession, instance: Any, *, actor: Any | None = None, **_: Any
    ) -> None:
        actual = getattr(instance, self.field)
        if actual not in self.allowed:
            raise GuardViolationError(
                code="state-not-allowed",
                ctx={"field": self.field, "actual": actual, "allowed": list(self.allowed)},
            )


class SelfProtection:
    """Forbid an action where the actor is the target. Bypassed for superadmins."""

    async def check(
        self, session: AsyncSession, instance: Any, *, actor: Any | None = None, **_: Any
    ) -> None:
        if actor is None:
            return
        # `is_superadmin` reads the selectin-loaded `roles` relationship; a
        # freshly-flushed (not-yet-queried) actor has no cache, so hydrate via
        # AsyncAttrs before touching the sync property.
        await actor.awaitable_attrs.roles
        if actor.is_superadmin:
            return
        if getattr(actor, "id", None) == getattr(instance, "id", None):
            raise GuardViolationError(
                code="self-protection",
                ctx={"actor_id": str(actor.id), "target_id": str(instance.id)},
            )


class ServiceBase:
    model: type

    async def delete(
        self, session: AsyncSession, instance: Any, *, actor: Any | None = None, **kwargs: Any
    ) -> None:
        guards = getattr(self.model, "__guards__", {}).get("delete", [])
        for guard in guards:
            await guard.check(session, instance, actor=actor, **kwargs)
        async with session.begin():
            await session.delete(instance)
