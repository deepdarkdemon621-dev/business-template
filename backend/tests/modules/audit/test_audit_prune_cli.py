from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli_commands.audit import run_prune
from app.modules.audit.models import AuditEvent


async def test_prune_removes_rows_older_than_cutoff(db_session: AsyncSession) -> None:
    # seed 10 events at T-400d (should be pruned), 10 events at T-100d (should survive)
    old_ts = datetime.now(UTC) - timedelta(days=400)
    new_ts = datetime.now(UTC) - timedelta(days=100)
    for _ in range(10):
        db_session.add(
            AuditEvent(
                id=uuid.uuid4(),
                occurred_at=old_ts,
                event_type="t12.old",
                action="update",
            )
        )
    for _ in range(10):
        db_session.add(
            AuditEvent(
                id=uuid.uuid4(),
                occurred_at=new_ts,
                event_type="t12.new",
                action="update",
            )
        )
    await db_session.commit()

    # run prune with 365-day cutoff and small chunk_size to force multi-chunk.
    # Inject db_session so run_prune operates on the same connection and can
    # see rows committed inside the per-test transaction.
    deleted, chunks = await run_prune(older_than_days=365, chunk_size=7, _session=db_session)
    assert deleted == 10
    assert chunks >= 2  # 10 rows / chunk_size 7 → 2 chunks

    remaining_types = (
        await db_session.execute(
            select(AuditEvent.event_type).where(
                AuditEvent.event_type.in_(["t12.old", "t12.new"])
            ).distinct()
        )
    ).scalars().all()
    assert "t12.old" not in remaining_types
    assert "t12.new" in remaining_types


async def test_prune_emits_self_event(db_session: AsyncSession) -> None:
    old_ts = datetime.now(UTC) - timedelta(days=400)
    db_session.add(
        AuditEvent(
            id=uuid.uuid4(),
            occurred_at=old_ts,
            event_type="t12_self.old",
            action="update",
        )
    )
    await db_session.commit()

    await run_prune(older_than_days=365, _session=db_session)

    ev = (
        await db_session.execute(
            select(AuditEvent)
            .where(AuditEvent.event_type == "audit.pruned")
            .order_by(AuditEvent.occurred_at.desc())
            .limit(1)
        )
    ).scalar_one()
    assert ev.metadata_["deleted_count"] >= 1
    assert "cutoff" in ev.metadata_
