"""Business logic layer.

Rules:
- All write ops via service, not directly from router.
- Service methods run inside `async with session.begin()` (one transaction per call).
- Run __guards__ before mutations (see 02-service-guards).
- Emit audit events for every mutation (handled by service base in Plan 2).
"""
