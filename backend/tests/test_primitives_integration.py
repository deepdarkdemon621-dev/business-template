"""Smoke test: wire a fake 'items' resource that uses every Plan 2 primitive
and assert the composed behavior. Intentionally throwaway — Plan 3's first
real endpoint supersedes it.
"""
from typing import Annotated
from unittest.mock import AsyncMock, MagicMock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.errors import GuardViolationCtx, ProblemDetails, install_handlers
from app.core.guards import GuardViolationError, NoDependents, ServiceBase
from app.core.pagination import Page, PageQuery, paginate
from app.core.schemas import BaseSchema


class ItemRead(BaseSchema):
    id: int
    display_name: str


class _FakeItem:
    __tablename__ = "items"
    __guards__ = {"delete": [NoDependents(relation="sub_items", fk_col="item_id")]}

    def __init__(self, id: int, name: str):
        self.id = id
        self.display_name = name


class _ItemService(ServiceBase):
    model = _FakeItem


def _make_app_and_session():
    app = FastAPI()
    install_handlers(app)

    session = AsyncMock()

    async def get_session():
        return session

    @app.get("/items", response_model=Page[ItemRead])
    async def list_items(
        s: Annotated[AsyncMock, Depends(get_session)],
        pq: Annotated[PageQuery, Depends()],
    ):
        from sqlalchemy import select
        stmt = select(1)  # placeholder — mock handles the actual return
        return await paginate(s, stmt, pq)

    @app.delete("/items/{item_id}", status_code=204)
    async def delete_item(
        item_id: int,
        s: Annotated[AsyncMock, Depends(get_session)],
    ):
        instance = _FakeItem(id=item_id, name="dummy")
        try:
            await _ItemService().delete(s, instance)
        except GuardViolationError as e:
            raise ProblemDetails(
                code="item.has-dependents",
                status=409,
                detail="Cannot delete item with dependents.",
                guard_violation=GuardViolationCtx(guard="NoDependents", params=e.ctx),
            )

    return TestClient(app), session


def _prime_list(session, total: int, items: list):
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    row_result = MagicMock()
    row_result.scalars.return_value.all.return_value = items
    session.execute.side_effect = [count_result, row_result]


def test_list_endpoint_returns_page_shape():
    client, session = _make_app_and_session()
    _prime_list(session, total=3, items=[_FakeItem(i, f"item-{i}") for i in range(1, 4)])

    r = client.get("/items?page=1&size=5")
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "items": [
            {"id": 1, "displayName": "item-1"},
            {"id": 2, "displayName": "item-2"},
            {"id": 3, "displayName": "item-3"},
        ],
        "total": 3,
        "page": 1,
        "size": 5,
        "hasNext": False,
    }


def test_size_clamped_silently():
    client, session = _make_app_and_session()
    _prime_list(session, total=0, items=[])
    r = client.get("/items?size=500")
    assert r.status_code == 200
    assert r.json()["size"] == 100


def test_delete_triggers_guard_and_returns_problem_details():
    client, session = _make_app_and_session()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 7  # dependents exist
    session.execute.return_value = count_result

    r = client.delete("/items/1")
    assert r.status_code == 409
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body["code"] == "item.has-dependents"
    assert body["guardViolation"]["guard"] == "NoDependents"
    assert body["guardViolation"]["params"]["count"] == 7
