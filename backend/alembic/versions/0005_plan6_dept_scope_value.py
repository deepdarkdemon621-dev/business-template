"""plan6 departments scope_value + department perms

Revision ID: 0005_plan6_dept_scope_value
Revises: 0004_plan5_user_assign_perm
Create Date: 2026-04-21
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# Keep revision <= 32 chars — alembic_version.version_num is VARCHAR(32).
revision = "0005_plan6_dept_scope_value"
down_revision = "0004_plan5_user_assign_perm"
branch_labels = None
depends_on = None


_NEW_ACTIONS = (
    "create",
    "read",
    "update",
    "delete",
    "list",
    "export",
    "approve",
    "reject",
    "publish",
    "invoke",
    "assign",
    "move",
)

_OLD_ACTIONS = _NEW_ACTIONS[:-1]  # without 'move'

# Note on scope: migration 0003 seeds 5 `department:*` permissions
# (create/read/update/delete/list). This migration adds a 6th (`move`) and uses
# ON CONFLICT (code) DO NOTHING on create/read/update/delete for self-containment
# — intentionally omitting `list` per Plan 6 scope addendum 1 ("department:list
# left dormant"). The migration is idempotent: if a future migration re-seeds,
# this one still converges on the expected end state.
_DEPARTMENT_PERMS = (
    ("department:create", "create", "Create a department"),
    ("department:read", "read", "Read / list / tree view departments"),
    ("department:update", "update", "Rename a department"),
    ("department:delete", "delete", "Soft-delete a department"),
    ("department:move", "move", "Move a department under a new parent"),
)

_DEPT_CODES_SQL = (
    "'department:create','department:read','department:update',"
    "'department:delete','department:move'"
)


def _action_check_sql(actions: tuple[str, ...]) -> str:
    literals = ",".join(f"'{a}'" for a in actions)
    return f"action IN ({literals})"


def upgrade() -> None:
    # --- 1. user_roles.scope_value column + partial index ---
    op.add_column(
        "user_roles",
        sa.Column(
            "scope_value",
            UUID(as_uuid=True),
            sa.ForeignKey("departments.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_user_roles_scope_value",
        "user_roles",
        ["scope_value"],
        postgresql_where=sa.text("scope_value IS NOT NULL"),
    )

    # --- 2. Extend permissions.action CHECK to include 'move' ---
    op.drop_constraint("ck_permissions_action", "permissions", type_="check")
    op.create_check_constraint(
        "ck_permissions_action",
        "permissions",
        _action_check_sql(_NEW_ACTIONS),
    )

    # --- 3. Seed 5 department permissions (4 already exist from 0003) ---
    # Use ON CONFLICT DO NOTHING on the unique `code` column so this migration
    # is a no-op for the 4 overlapping perms and only actually inserts 'move'.
    bind = op.get_bind()
    for code, action, description in _DEPARTMENT_PERMS:
        bind.execute(
            sa.text(
                "INSERT INTO permissions (id, code, resource, action, description) "
                "VALUES (:id, :code, :resource, :action, :description) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {
                "id": uuid.uuid4(),
                "code": code,
                "resource": "department",
                "action": action,
                "description": description,
            },
        )

    # --- 4. Grant all 5 to built-in admin at global scope ---
    # 4 grants already exist from 0003; ON CONFLICT on the composite PK keeps
    # this idempotent and only inserts the new 'department:move' grant.
    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, permission_id, scope)
        SELECT r.id, p.id, 'global'
        FROM roles r, permissions p
        WHERE r.code = 'admin'
          AND p.code IN ({_DEPT_CODES_SQL})
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )


def downgrade() -> None:
    # --- 1. Drop scope_value column + partial index ---
    op.drop_index("ix_user_roles_scope_value", table_name="user_roles")
    op.drop_column("user_roles", "scope_value")

    # --- 2. Remove the 'department:move' grant + perm only. ---
    # The other 4 department perms predate this migration (0003) — leave them.
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code = 'department:move')"
    )
    op.execute("DELETE FROM permissions WHERE code = 'department:move'")

    # --- 3. Restore original action CHECK (no 'move'). ---
    # Must happen AFTER removing any 'move' rows so the new constraint validates.
    op.drop_constraint("ck_permissions_action", "permissions", type_="check")
    op.create_check_constraint(
        "ck_permissions_action",
        "permissions",
        _action_check_sql(_OLD_ACTIONS),
    )
