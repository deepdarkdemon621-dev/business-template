from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.schemas import BaseSchema

MAX_PAGE_SIZE = 100


class PageQuery(BaseModel):
    page: int = Field(default=1)
    size: int = Field(default=20)
    sort: str | None = None
    q: str | None = None

    @field_validator("page", mode="before")
    @classmethod
    def _clamp_page(cls, v: Any) -> int:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 1
        return max(1, n)

    @field_validator("size", mode="before")
    @classmethod
    def _clamp_size(cls, v: Any) -> int:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 20
        return max(1, min(MAX_PAGE_SIZE, n))


class Page[T](BaseSchema):
    items: list[T]
    total: int
    page: int
    size: int
    has_next: bool


async def paginate(
    session: AsyncSession,
    stmt: Select,
    pq: PageQuery,
) -> Page[Any]:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    offset = (pq.page - 1) * pq.size
    rows_stmt = stmt.offset(offset).limit(pq.size)
    rows_result = await session.execute(rows_stmt)
    items = list(rows_result.scalars().all())

    has_next = (pq.page * pq.size) < total
    return Page(items=items, total=total, page=pq.page, size=pq.size, has_next=has_next)
