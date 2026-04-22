from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rbac.models import Department

_GUARDS_KEY = "move"
_SLUG_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _slugify(name: str) -> str:
    s = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return s or "dept"


class DepartmentService:
    """Business operations on Department beyond simple field edits."""

    async def move_department(
        self,
        session: AsyncSession,
        dept: Department,
        *,
        new_parent_id: uuid.UUID,
        actor: Any | None = None,
    ) -> None:
        # 1. Run guards first (NoCycle rejects self-parent + descendant cycles).
        for guard in getattr(Department, "__guards__", {}).get(_GUARDS_KEY, []):
            await guard.check(session, dept, actor=actor, new_parent_id=new_parent_id)

        # 2. Resolve new parent; refuse if missing.
        new_parent = await session.get(Department, new_parent_id)
        if new_parent is None:
            # Treated as 404 upstream by the router via load_in_scope patterns.
            raise ValueError(f"Parent {new_parent_id} not found.")

        old_prefix = dept.path
        # No-op if it's already a direct child of new_parent.
        expected_parent_prefix = new_parent.path
        if dept.parent_id == new_parent_id and dept.path.startswith(expected_parent_prefix):
            return

        # 3. Compute new path for this node.
        #    Path segment re-uses the trailing slug (last non-empty component of
        #    old_prefix) to preserve stable URLs under the new parent.
        segments = [s for s in old_prefix.split("/") if s]
        leaf_segment = segments[-1] if segments else _slugify(dept.name)
        new_prefix = f"{new_parent.path}{leaf_segment}/"

        # 4. Update every row whose path starts with old_prefix (self + descendants).
        #    Depth is recalculated as the delta between the old and new prefixes.
        depth_delta = new_prefix.count("/") - old_prefix.count("/")
        rows_stmt = select(Department).where(Department.path.like(f"{old_prefix}%"))
        for row in (await session.execute(rows_stmt)).scalars().all():
            row.path = new_prefix + row.path[len(old_prefix) :]
            row.depth = row.depth + depth_delta

        # 5. Update dept.parent_id explicitly (only the moved node's parent changes).
        dept.parent_id = new_parent_id

        await session.flush()
