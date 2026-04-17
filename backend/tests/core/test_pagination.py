from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.core.pagination import PageQuery, paginate


def _mock_session(total: int, rows: list):
    session = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    row_result = MagicMock()
    row_result.scalars.return_value.all.return_value = rows
    session.execute.side_effect = [count_result, row_result]
    return session


@pytest.fixture
def stmt():
    return select(1)


async def test_page_one_has_next(stmt):
    session = _mock_session(total=42, rows=[{"id": i} for i in range(20)])
    page = await paginate(session, stmt, PageQuery(page=1, size=20))
    assert page.total == 42
    assert page.page == 1
    assert page.size == 20
    assert page.has_next is True
    assert len(page.items) == 20


async def test_last_page_has_next_false(stmt):
    session = _mock_session(total=42, rows=[{"id": i} for i in range(2)])
    page = await paginate(session, stmt, PageQuery(page=3, size=20))
    assert page.has_next is False
    assert len(page.items) == 2


async def test_size_above_cap_is_clamped_to_100(stmt):
    pq = PageQuery.model_validate({"page": 1, "size": 500})
    assert pq.size == 100


async def test_size_below_one_is_clamped_to_one(stmt):
    pq = PageQuery.model_validate({"page": 1, "size": 0})
    assert pq.size == 1


async def test_page_below_one_is_clamped_to_one(stmt):
    pq = PageQuery.model_validate({"page": -2, "size": 20})
    assert pq.page == 1
