# backend/tests/modules/audit/test_audit_api.py
from __future__ import annotations

import uuid
from types import SimpleNamespace

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import audit


async def test_list_without_perm_403(member_token: tuple[AsyncClient, str]) -> None:
    client, token = member_token
    res = await client.get(
        "/api/v1/audit-events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "permission.denied"


async def test_list_with_superadmin_200(
    superadmin_token: tuple[AsyncClient, str],
    db_session: AsyncSession,
    db_audit_ctx,
) -> None:
    client, token = superadmin_token
    u = SimpleNamespace(id=uuid.uuid4(), email="evt@x", full_name="E", is_active=True, department_id=None)
    await audit.user_created(db_session, u)
    await db_session.commit()
    res = await client.get(
        "/api/v1/audit-events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert "items" in body
    # list response must exclude diff fields
    first = body["items"][0]
    for forbidden in ("before", "after", "changes", "metadata"):
        assert forbidden not in first


async def test_list_filter_by_event_type(
    superadmin_token: tuple[AsyncClient, str],
    db_session: AsyncSession,
    db_audit_ctx,
) -> None:
    client, token = superadmin_token
    u = SimpleNamespace(id=uuid.uuid4(), email="f@x", full_name="F", is_active=True, department_id=None)
    await audit.user_created(db_session, u)
    await audit.user_updated(db_session, u, {"full_name": ["A", "B"]})
    await db_session.commit()
    res = await client.get(
        "/api/v1/audit-events?event_type=user.created",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert all(it["eventType"] == "user.created" for it in body["items"])


async def test_detail_returns_full_payload(
    superadmin_token: tuple[AsyncClient, str],
    db_session: AsyncSession,
    db_audit_ctx,
) -> None:
    client, token = superadmin_token
    u = SimpleNamespace(id=uuid.uuid4(), email="d@x", full_name="D", is_active=True, department_id=None)
    ev = await audit.user_created(db_session, u)
    await db_session.commit()
    res = await client.get(
        f"/api/v1/audit-events/{ev.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["eventType"] == "user.created"
    assert body["after"]["email"] == "d@x"
    # Verify ORM attr name doesn't leak through the dual-alias
    assert "metadata_" not in body


async def test_detail_404_for_unknown_id(
    superadmin_token: tuple[AsyncClient, str],
) -> None:
    client, token = superadmin_token
    res = await client.get(
        f"/api/v1/audit-events/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "audit.not-found"


async def test_list_rejects_invalid_sort(
    superadmin_token: tuple[AsyncClient, str],
) -> None:
    client, token = superadmin_token
    res = await client.get(
        "/api/v1/audit-events?sort=banana",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert res.json()["code"] == "audit.invalid-sort"
