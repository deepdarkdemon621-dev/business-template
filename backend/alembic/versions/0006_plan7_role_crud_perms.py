"""plan7 role crud permissions

Revision ID: 0006_plan7_role_crud_perms
Revises: 0005_plan6_dept_scope_value
Create Date: 2026-04-22
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0006_plan7_role_crud_perms"
down_revision: str | None = "0005_plan6_dept_scope_value"
branch_labels = None
depends_on = None


_NEW_PERMISSIONS = [
    ("role:create", "role", "create", "Create a role"),
    ("role:update", "role", "update", "Update role metadata or permissions"),
    ("role:delete", "role", "delete", "Delete a non-builtin role"),
]


def upgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.String),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", UUID(as_uuid=True)),
        sa.column("permission_id", UUID(as_uuid=True)),
        sa.column("scope", sa.String),
    )
    roles = sa.table(
        "roles",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("code", sa.String),
    )

    conn = op.get_bind()
    admin_row = conn.execute(sa.select(roles.c.id).where(roles.c.code == "admin")).first()
    if admin_row is None:
        # Seeds not run yet (fresh DB via pure alembic); skip grants.
        admin_id = None
    else:
        admin_id = admin_row[0]

    for code, resource, action, desc in _NEW_PERMISSIONS:
        pid = uuid.uuid4()
        conn.execute(
            permissions.insert().values(
                id=pid, code=code, resource=resource, action=action, description=desc
            )
        )
        if admin_id is not None:
            conn.execute(
                role_permissions.insert().values(
                    role_id=admin_id, permission_id=pid, scope="global"
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    codes = [p[0] for p in _NEW_PERMISSIONS]
    # Delete dependent role_permissions first (no CASCADE triggered by DELETE on permissions).
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    conn.execute(
        sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"),
        {"codes": codes},
    )
