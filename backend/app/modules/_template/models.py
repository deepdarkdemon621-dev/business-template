"""SQLAlchemy ORM models for this module.

Rules:
- Use Mapped[] / mapped_column() (SQLAlchemy 2.0 style).
- Inherit from app.core.database.Base (added in Plan 2).
- Declare __guards__ for delete / state transitions (see 02-service-guards).
"""
