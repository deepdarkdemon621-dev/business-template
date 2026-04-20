"""plan4 rbac tables + seed

Revision ID: 0003
Revises: 8235ef11213e
Create Date: 2026-04-20
"""

from __future__ import annotations

import os
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0003"
down_revision = "8235ef11213e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- departments ---
    op.create_table(
        "departments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("departments.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("depth", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("parent_id", "name", name="uq_departments_parent_name"),
    )
    op.create_index("ix_departments_path", "departments", ["path"])
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"])

    # --- permissions ---
    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("resource", sa.String(50), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "action IN ('create','read','update','delete','list','export','approve','reject','publish','invoke','assign')",
            name="ck_permissions_action",
        ),
    )
    op.create_index("ix_permissions_resource_action", "permissions", ["resource", "action"])

    # --- roles ---
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_builtin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "is_superadmin", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- role_permissions ---
    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id",
            UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            UUID(as_uuid=True),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.CheckConstraint(
            "scope IN ('global','dept_tree','dept','own')",
            name="ck_role_permissions_scope",
        ),
    )

    # --- user_roles ---
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "granted_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )

    # --- users.department_id FK + index ---
    # Plan 3's 0002 migration already created `users.department_id` as a plain
    # UUID column (no FK). Promote it to a real FK + indexed column here.
    op.create_foreign_key(
        "fk_users_department_id",
        "users",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_department_id", "users", ["department_id"])

    # Seed data
    _seed(op.get_bind())


def downgrade() -> None:
    # Clear dangling refs so a later re-upgrade can re-create the FK cleanly.
    op.execute("UPDATE users SET department_id = NULL")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_constraint("fk_users_department_id", "users", type_="foreignkey")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_index("ix_permissions_resource_action", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_departments_parent_id", table_name="departments")
    op.drop_index("ix_departments_path", table_name="departments")
    op.drop_table("departments")


_PERMISSIONS = [
    # (code, resource, action, description)
    ("user:create", "user", "create", "Create a user"),
    ("user:read", "user", "read", "Read a user"),
    ("user:update", "user", "update", "Update a user"),
    ("user:delete", "user", "delete", "Delete a user"),
    ("user:list", "user", "list", "List users"),
    ("role:read", "role", "read", "Read a role"),
    ("role:list", "role", "list", "List roles"),
    ("role:assign", "role", "assign", "Assign a role to a user"),
    ("department:create", "department", "create", "Create a department"),
    ("department:read", "department", "read", "Read a department"),
    ("department:update", "department", "update", "Update a department"),
    ("department:delete", "department", "delete", "Delete a department"),
    ("department:list", "department", "list", "List departments"),
    ("permission:read", "permission", "read", "Read a permission"),
    ("permission:list", "permission", "list", "List permissions"),
]


def _seed(conn) -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.String),
    )
    perm_ids: dict[str, uuid.UUID] = {}
    for code, resource, action, desc in _PERMISSIONS:
        pid = uuid.uuid4()
        perm_ids[code] = pid
        conn.execute(
            permissions_table.insert().values(
                id=pid,
                code=code,
                resource=resource,
                action=action,
                description=desc,
            )
        )
    _seed_roles(conn, perm_ids)
    _seed_root_dept_and_admin(conn)


def _seed_roles(conn, perm_ids: dict[str, uuid.UUID]) -> None:
    roles_table = sa.table(
        "roles",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("is_builtin", sa.Boolean),
        sa.column("is_superadmin", sa.Boolean),
    )
    role_perm_table = sa.table(
        "role_permissions",
        sa.column("role_id", UUID(as_uuid=True)),
        sa.column("permission_id", UUID(as_uuid=True)),
        sa.column("scope", sa.String),
    )

    # superadmin — no role_permissions rows (short-circuits via is_superadmin)
    superadmin_id = uuid.uuid4()
    conn.execute(
        roles_table.insert().values(
            id=superadmin_id,
            code="superadmin",
            name="Super Administrator",
            is_builtin=True,
            is_superadmin=True,
        )
    )

    # admin — all 15 codes at scope=global
    admin_id = uuid.uuid4()
    conn.execute(
        roles_table.insert().values(
            id=admin_id,
            code="admin",
            name="Administrator",
            is_builtin=True,
            is_superadmin=False,
        )
    )
    for _code, pid in perm_ids.items():
        conn.execute(
            role_perm_table.insert().values(
                role_id=admin_id, permission_id=pid, scope="global",
            )
        )

    # member — narrow read set
    member_id = uuid.uuid4()
    conn.execute(
        roles_table.insert().values(
            id=member_id,
            code="member",
            name="Member",
            is_builtin=True,
            is_superadmin=False,
        )
    )
    member_grants = [
        ("user:read", "own"),
        ("role:read", "global"),
        ("role:list", "global"),
        ("department:read", "dept_tree"),
        ("department:list", "dept_tree"),
        ("permission:read", "global"),
        ("permission:list", "global"),
    ]
    for code, scope in member_grants:
        conn.execute(
            role_perm_table.insert().values(
                role_id=member_id,
                permission_id=perm_ids[code],
                scope=scope,
            )
        )


def _seed_root_dept_and_admin(conn) -> None:
    departments_table = sa.table(
        "departments",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("parent_id", UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("path", sa.String),
        sa.column("depth", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )

    root_name = os.environ.get("SEED_ROOT_DEPT_NAME", "Root")
    root_id = uuid.uuid4()
    conn.execute(departments_table.insert().values(
        id=root_id, parent_id=None, name=root_name,
        path=f"/{root_id}", depth=0, is_active=True,
    ))

    # Promote admin@example.com → superadmin and assign to root dept (if user exists)
    conn.execute(sa.text(
        """
        INSERT INTO user_roles (user_id, role_id, granted_at)
        SELECT u.id, r.id, now()
        FROM users u, roles r
        WHERE u.email = 'admin@example.com' AND r.code = 'superadmin'
        ON CONFLICT DO NOTHING
        """
    ))
    conn.execute(sa.text(
        "UPDATE users SET department_id = :dept WHERE email = 'admin@example.com'"
    ), {"dept": root_id})
