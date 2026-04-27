"""Audit log CLI. Invoked as: uv run python -m typer app.cli_commands.audit run"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import typer
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session as _session_factory
from app.modules.audit.context import AuditContext, audit_context
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import audit

app = typer.Typer(no_args_is_help=True)


@asynccontextmanager
async def _get_session(session: AsyncSession | None) -> AsyncIterator[AsyncSession]:
    """Yield *session* if provided (test injection), else open a new one."""
    if session is not None:
        yield session
    else:
        async with _session_factory() as s:
            yield s


async def run_prune(
    older_than_days: int = 365,
    chunk_size: int = 10_000,
    *,
    _session: AsyncSession | None = None,
) -> tuple[int, int]:
    """Delete audit events older than cutoff in chunks. Emits a self-event on completion.

    Returns (total_deleted, chunks_processed).

    Args:
        older_than_days: Delete events older than this many days.
        chunk_size: Rows to delete per commit.
        _session: Injected session for testing. Production callers leave this None.
    """
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    total_deleted = 0
    chunks = 0

    # Set CLI actor context before any DB work so the self-event has it.
    audit_context.set(
        AuditContext(actor_user_id=None, actor_ip=None, actor_user_agent="cli/prune")
    )

    async with _get_session(_session) as session:
        while True:
            ids = (
                await session.execute(
                    select(AuditEvent.id)
                    .where(AuditEvent.occurred_at < cutoff)
                    .limit(chunk_size)
                )
            ).scalars().all()
            if not ids:
                break
            await session.execute(delete(AuditEvent).where(AuditEvent.id.in_(ids)))
            await session.commit()
            total_deleted += len(ids)
            chunks += 1
            if len(ids) < chunk_size:
                break
        await audit.pruned(session, cutoff=cutoff, deleted_count=total_deleted, chunks=chunks)
        await session.commit()
    return total_deleted, chunks


@app.command("prune")
def prune(
    older_than_days: int = typer.Option(365, help="Delete events older than this many days."),
    chunk_size: int = typer.Option(10_000, help="Rows to delete per commit."),
) -> None:
    """Prune audit events older than the cutoff. Emits a self-audit event."""
    deleted, chunks = asyncio.run(run_prune(older_than_days=older_than_days, chunk_size=chunk_size))
    typer.echo(f"Pruned {deleted} events in {chunks} chunks (cutoff={older_than_days} days).")
