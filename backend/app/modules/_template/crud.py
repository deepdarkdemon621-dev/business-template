"""Data access helpers (pure DB queries).

Rules:
- Never call .all() bare — use paginate() for list, .scalar_one() for single.
- Must take AsyncSession as an argument; never create one.
"""
