from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


class GuardViolationError(Exception):
    def __init__(self, *, code: str, ctx: dict[str, Any]) -> None:
        self.code = code
        self.ctx = ctx
        super().__init__(code)


@runtime_checkable
class Guard(Protocol):
    async def check(self, session: AsyncSession, instance: Any) -> None: ...


class NoDependents:
    def __init__(self, relation: str, fk_col: str) -> None:
        self.relation = relation
        self.fk_col = fk_col

    async def check(self, session: AsyncSession, instance: Any) -> None:
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

    async def check(self, session: AsyncSession, instance: Any) -> None:
        actual = getattr(instance, self.field)
        if actual not in self.allowed:
            raise GuardViolationError(
                code="state-not-allowed",
                ctx={"field": self.field, "actual": actual, "allowed": list(self.allowed)},
            )


class ServiceBase:
    model: type

    async def delete(self, session: AsyncSession, instance: Any) -> None:
        guards = getattr(self.model, "__guards__", {}).get("delete", [])
        for guard in guards:
            await guard.check(session, instance)
        await session.delete(instance)
