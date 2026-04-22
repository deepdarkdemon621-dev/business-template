from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemDetails
from app.modules.department.schemas import DepartmentCreateIn, DepartmentUpdateIn
from app.modules.rbac.models import Department

_SLUG_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _slugify(name: str) -> str:
    s = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return s or "dept"


def build_list_flat_stmt(is_active: bool | None = True) -> Select[tuple[Department]]:
    stmt = select(Department).order_by(Department.depth, Department.name)
    if is_active is not None:
        stmt = stmt.where(Department.is_active.is_(is_active))
    return stmt


async def get_department(session: AsyncSession, dept_id: uuid.UUID) -> Department | None:
    return await session.get(Department, dept_id)


async def create_department(session: AsyncSession, payload: DepartmentCreateIn) -> Department:
    parent = await session.get(Department, payload.parent_id)
    if parent is None:
        raise ProblemDetails(
            code="resource.not-found",
            status=404,
            detail=f"Parent department {payload.parent_id} not found.",
        )
    new_id = uuid.uuid4()
    child_slug = _slugify(payload.name)
    # Append a short uid suffix to guarantee path uniqueness even if two
    # children share the same slugified name.
    suffix = str(new_id)[:8]
    child_path = f"{parent.path}{child_slug}-{suffix}/"
    d = Department(
        id=new_id,
        parent_id=parent.id,
        name=payload.name,
        path=child_path,
        depth=parent.depth + 1,
    )
    session.add(d)
    await session.flush()
    return d


async def update_department(
    session: AsyncSession, target: Department, payload: DepartmentUpdateIn
) -> Department:
    target.name = payload.name
    await session.flush()
    return target


async def soft_delete_department(
    session: AsyncSession, target: Department, *, actor: Any | None
) -> None:
    # Guards dispatched by the service layer.
    target.is_active = False
    await session.flush()


async def get_tree_rooted_at(
    session: AsyncSession,
    *,
    root_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[Department]:
    """Return every department in the subtree rooted at `root_id` (or the whole
    forest if `root_id` is None), ordered by depth then name.
    """
    stmt = select(Department).order_by(Department.depth, Department.name)
    if not include_inactive:
        stmt = stmt.where(Department.is_active.is_(True))
    if root_id is not None:
        root = await session.get(Department, root_id)
        if root is None:
            return []
        stmt = stmt.where(Department.path.like(f"{root.path}%"))
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)
