"""plan8 audit log viewer

Revision ID: 0007_plan8_audit_log
Revises: 0006_plan7_role_crud_perms
Create Date: 2026-04-24
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID

revision: str = "0007_plan8_audit_log"
down_revision: str | None = "0006_plan7_role_crud_perms"
branch_labels = None
depends_on = None


_NEW_PERMISSIONS = [
    ("audit:list", "audit", "list", "List audit events"),
    ("audit:read", "audit", "read", "Read audit event detail"),
]


def upgrade() -> None:
    # 1. audit_events table
    op.create_table(
        "audit_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column(
            "actor_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_ip", INET, nullable=True),
        sa.Column("actor_user_agent", sa.String(512), nullable=True),
        sa.Column("resource_type", sa.String(32), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("resource_label", sa.String(255), nullable=True),
        sa.Column("before", JSONB, nullable=True),
        sa.Column("after", JSONB, nullable=True),
        sa.Column("changes", JSONB, nullable=True),
        # Named event_metadata to avoid collision with SQLAlchemy's Base.metadata.
        # ORM in Task 2 will map this to metadata_ on the Python side.
        sa.Column("event_metadata", JSONB, nullable=True),
    )
    op.create_index(
        "ix_audit_events_occurred_at_desc",
        "audit_events",
        [sa.text("occurred_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_audit_events_actor",
        "audit_events",
        ["actor_user_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_audit_events_resource",
        "audit_events",
        ["resource_type", "resource_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_audit_events_action",
        "audit_events",
        ["action", sa.text("occurred_at DESC")],
    )

    # 2. users.last_login_at
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_users_last_login_at",
        "users",
        [sa.text("last_login_at DESC NULLS LAST")],
    )

    # 3. Seed audit perms + grant to superadmin
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
    sa_row = conn.execute(
        sa.select(roles.c.id).where(roles.c.code == "superadmin")
    ).first()
    superadmin_id = None if sa_row is None else sa_row[0]
    for code, resource, action, desc in _NEW_PERMISSIONS:
        pid = uuid.uuid4()
        conn.execute(
            permissions.insert().values(
                id=pid,
                code=code,
                resource=resource,
                action=action,
                description=desc,
            )
        )
        if superadmin_id is not None:
            conn.execute(
                role_permissions.insert().values(
                    role_id=superadmin_id,
                    permission_id=pid,
                    scope="global",
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
    op.drop_index("ix_users_last_login_at", table_name="users")
    op.drop_column("users", "last_login_at")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_resource", table_name="audit_events")
    op.drop_index("ix_audit_events_actor", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at_desc", table_name="audit_events")
    op.drop_table("audit_events")
