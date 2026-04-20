import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rbac.models import Department


@pytest.mark.asyncio
async def test_department_insert_and_path(db_session: AsyncSession):
    root = Department(name="Root", path="/root-uuid", depth=0, parent_id=None)
    db_session.add(root)
    await db_session.flush()
    result = await db_session.execute(select(Department).where(Department.id == root.id))
    fetched = result.scalar_one()
    assert fetched.name == "Root"
    assert fetched.depth == 0
    assert fetched.is_active is True
