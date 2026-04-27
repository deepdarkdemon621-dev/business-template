from __future__ import annotations

import uuid
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.audit.service import audit


async def test_audit_row_rolls_back_with_outer_tx(db_session: AsyncSession, db_audit_ctx):
    """AuditEvent rows must roll back with the outer transaction.

    AuditService.user_created() inserts a row without committing — the
    commit belongs to the caller. If the caller rolls back (e.g. due to a
    business-logic error after the audit.record call), the audit row must
    disappear with it.

    db_session is backed by a raw connection with a begin()-level transaction.
    Calling rollback() on the session cancels that transaction. Subsequent
    SELECTs auto-begin a new (empty) transaction.
    """
    u = SimpleNamespace(
        id=uuid.uuid4(),
        email="rollback@example.com",
        full_name="Rollback Test",
        is_active=True,
        department_id=None,
    )
    # Write the audit row (flush-only, not committed).
    await audit.user_created(db_session, u)

    # Simulate the outer service discovering an error AFTER audit.record but
    # BEFORE commit — the entire unit of work rolls back.
    await db_session.rollback()

    # After rollback the row must be gone.  A new implicit transaction is
    # started by the SELECT; the previously written row is not visible.
    rows = (
        await db_session.execute(
            select(AuditEvent).where(AuditEvent.resource_label == "rollback@example.com")
        )
    ).scalars().all()
    assert rows == [], "AuditEvent row must not be visible after outer-transaction rollback"
