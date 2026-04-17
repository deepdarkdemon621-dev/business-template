from __future__ import annotations


async def public_endpoint() -> None:
    """No-op dependency that marks a route as intentionally public (no auth required)."""
