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
    # Grant user:assign to the admin built-in role so a fresh upgrade head
    # leaves admin with the same permissions as superadmin (minus bypass).
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id, scope)
        SELECT r.id, p.id, 'global'
        FROM roles r, permissions p
        WHERE r.code = 'admin' AND p.code = 'user:assign'
    """)


def downgrade() -> None:
    # Delete FK-dependent row before the permission row itself.
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code = 'user:assign')"
    )
    op.execute("DELETE FROM permissions WHERE code = 'user:assign'")
