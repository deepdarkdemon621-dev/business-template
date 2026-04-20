"""plan5 seed user:assign permission

Revision ID: 0004_plan5_user_assign_perm
Revises: 0003
Create Date: 2026-04-20
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0004_plan5_user_assign_perm"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.String),
    )
    op.execute(
        permissions_table.insert().values(
            id=uuid.uuid4(),
            code="user:assign",
            resource="user",
            action="assign",
            description="Assign roles to a user",
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM permissions WHERE code = 'user:assign'")
