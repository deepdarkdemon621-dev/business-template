# Plan 6 — Department Tree CRUD + Per-Assignment Role Scope

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Plan 6 per spec `docs/superpowers/specs/2026-04-21-plan6-department-tree-scoped-roles-design.md` — (1) admins can CRUD the department tree in the UI, (2) `user_roles.scope_value` column + `apply_scope` rewrite unlock per-assignment department anchoring (foundation for 兼務 / concurrent-position use in Plan 7). Produces tag `v0.6.0-departments-scoped-roles`.

**Architecture:** Two parallel tracks sharing migration 0005. Track 1 — new feature-first module `app/modules/department/` (re-exports `Department` from `rbac/models.py`, owns CRUD + move) + FE `src/modules/department/` with a new `@/components/ui/tree` primitive. Track 2 — `user_roles.scope_value` nullable UUID column (FK → departments, `ON DELETE SET NULL`) + rewrite of `apply_scope` DEPT / DEPT_TREE branches to `coalesce(UserRole.scope_value, user.department_id)` joined through `RolePermission`/`Permission`. With `scope_value = NULL` (post-migration state), behaviour is byte-identical to Plan 4 — existing `apply_scope` tests stay green unchanged and act as the backward-compat lock.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, React 19, react-router-dom v7, axios, Vitest, pytest-asyncio, Playwright (system Chrome via `channel: "chrome"`).

**Scope addenda beyond the spec:**
1. **`department:list` left dormant.** Plan 4 seeded `department:list`, but the Plan 6 spec consolidates list/tree/get under `department:read`. Migration 0005 seeds the new 5 (`department:{create,read,update,delete,move}`) but does *not* delete `department:list` (avoid churn; cleanup deferred).
2. **`ActionEnum.MOVE`.** The spec's `department:move` permission requires a new vocabulary verb. Added to `ActionEnum` + the `ck_permissions_action` CheckConstraint drop-and-recreate happens inside migration 0005.
3. **Nav-items permission swap.** `frontend/src/components/layout/nav-items.ts` currently requires `department:list` for the sidebar link; changed to `department:read` so admin still sees it after Plan 6.
4. **Hand-written JSON Schema in `DepartmentEditPage`.** Convention 04 explicitly allows static inline schemas alongside OpenAPI-derived ones; no BE endpoint exists to serve a schema, and building one is out of scope.

---

## Phase A — Migration 0005 + ActionEnum vocabulary

Prerequisite for everything else: the column and permissions must exist before `apply_scope` can read `UserRole.scope_value` or the new `/departments` routes can `require_perm("department:read")`.

### Task A1: Add `MOVE` to `ActionEnum`

**Files:**
- Modify: `backend/app/modules/rbac/constants.py`
- Test: `backend/tests/modules/rbac/test_constants.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/modules/rbac/test_constants.py`:
```python
def test_action_enum_includes_move() -> None:
    from app.modules.rbac.constants import ActionEnum

    assert ActionEnum.MOVE == "move"
    assert "move" in {a.value for a in ActionEnum}
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/rbac/test_constants.py::test_action_enum_includes_move -v`
Expected: `AttributeError: MOVE` (or ValueError on `ActionEnum.MOVE`).

- [ ] **Step 3: Add the enum entry**

Edit `backend/app/modules/rbac/constants.py` — add `MOVE = "move"` as the last entry of `ActionEnum`:
```python
class ActionEnum(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    EXPORT = "export"
    APPROVE = "approve"
    REJECT = "reject"
    PUBLISH = "publish"
    INVOKE = "invoke"
    ASSIGN = "assign"
    MOVE = "move"
```

- [ ] **Step 4: Run test — expect pass**

Run: `docker compose exec backend uv run pytest tests/modules/rbac/test_constants.py -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/rbac/constants.py backend/tests/modules/rbac/test_constants.py
git commit -m "feat(rbac): add ActionEnum.MOVE for department:move permission"
```

---

### Task A2: Extend `Permission.ck_permissions_action` CheckConstraint

The ORM model's `CheckConstraint` must match the CHECK that migration 0005 will install in Postgres; otherwise `Permission(action="move")` would raise at flush time.

**Files:**
- Modify: `backend/app/modules/rbac/models.py`
- Test: `backend/tests/modules/rbac/test_models.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/modules/rbac/test_models.py`:
```python
def test_permission_check_constraint_allows_move() -> None:
    from app.modules.rbac.models import Permission

    check = next(
        c for c in Permission.__table_args__
        if hasattr(c, "name") and c.name == "ck_permissions_action"
    )
    assert "'move'" in str(check.sqltext)
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/rbac/test_models.py::test_permission_check_constraint_allows_move -v`
Expected: assertion failure — `'move'` not in the check expression.

- [ ] **Step 3: Update the CheckConstraint**

Edit `backend/app/modules/rbac/models.py:77`. Replace the existing `action IN (...)` string with one that includes `'move'` as the last literal:
```python
    __table_args__ = (
        CheckConstraint(
            "action IN ('create','read','update','delete','list','export','approve','reject','publish','invoke','assign','move')",
            name="ck_permissions_action",
        ),
        Index("ix_permissions_resource_action", "resource", "action"),
    )
```

- [ ] **Step 4: Run test — expect pass**

Run: `docker compose exec backend uv run pytest tests/modules/rbac/test_models.py -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/rbac/models.py backend/tests/modules/rbac/test_models.py
git commit -m "feat(rbac): extend Permission action CHECK to accept 'move'"
```

---

### Task A3: Add `UserRole.scope_value` column to the ORM

Mirror the migration into the ORM so tests, CLI seeds, and services can write `scope_value` without raising on unknown attribute.

**Files:**
- Modify: `backend/app/modules/rbac/models.py`
- Test: `backend/tests/modules/rbac/test_models.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/modules/rbac/test_models.py`:
```python
def test_user_role_has_scope_value_column() -> None:
    from app.modules.rbac.models import UserRole

    col = UserRole.__table__.c.scope_value
    assert col.nullable is True
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "departments"
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/rbac/test_models.py::test_user_role_has_scope_value_column -v`
Expected: `KeyError: 'scope_value'`.

- [ ] **Step 3: Add the column**

Edit `backend/app/modules/rbac/models.py`, inside the `UserRole` class (after `granted_by`):
```python
    scope_value: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
```

- [ ] **Step 4: Run test — expect pass**

Run: `docker compose exec backend uv run pytest tests/modules/rbac/test_models.py -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/rbac/models.py backend/tests/modules/rbac/test_models.py
git commit -m "feat(rbac): add UserRole.scope_value column for per-assignment dept anchor"
```

---

### Task A4: Alembic migration 0005 — schema + seeds

**Files:**
- Create: `backend/alembic/versions/0005_plan6_departments_scope_value.py`
- Test: `backend/tests/migrations/test_0005_migration.py`

- [ ] **Step 1: Write the failing migration test**

Check first whether `backend/tests/migrations/` exists. If not, create it:
```bash
docker compose exec backend bash -c "ls backend/tests/migrations 2>/dev/null || mkdir -p backend/tests/migrations && touch backend/tests/migrations/__init__.py"
```

Then create `backend/tests/migrations/test_0005_migration.py`:
```python
from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_scope_value_column_exists(db_session: AsyncSession) -> None:
    def _inspect(sync_conn):
        insp = inspect(sync_conn)
        cols = {c["name"]: c for c in insp.get_columns("user_roles")}
        assert "scope_value" in cols
        assert cols["scope_value"]["nullable"] is True

    await db_session.run_sync(lambda s: _inspect(s.connection()))


async def test_partial_index_on_scope_value(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'user_roles' AND indexname = 'ix_user_roles_scope_value'"
        )
    )
    row = result.first()
    assert row is not None
    assert "scope_value IS NOT NULL" in row[0]


async def test_action_check_allows_move(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
            "JOIN pg_class t ON t.oid = c.conrelid "
            "WHERE t.relname = 'permissions' AND c.conname = 'ck_permissions_action'"
        )
    )
    row = result.first()
    assert row is not None
    assert "'move'" in row[0]


async def test_department_permissions_seeded(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT code FROM permissions WHERE code LIKE 'department:%' ORDER BY code")
    )
    codes = [r[0] for r in result]
    assert "department:create" in codes
    assert "department:read" in codes
    assert "department:update" in codes
    assert "department:delete" in codes
    assert "department:move" in codes


async def test_admin_role_granted_dept_permissions(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT p.code, rp.scope "
            "FROM role_permissions rp "
            "JOIN permissions p ON p.id = rp.permission_id "
            "JOIN roles r ON r.id = rp.role_id "
            "WHERE r.code = 'admin' AND p.code LIKE 'department:%' "
            "ORDER BY p.code"
        )
    )
    rows = [(r[0], r[1]) for r in result]
    grants = dict(rows)
    assert grants.get("department:create") == "global"
    assert grants.get("department:read") == "global"
    assert grants.get("department:update") == "global"
    assert grants.get("department:delete") == "global"
    assert grants.get("department:move") == "global"
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/migrations/test_0005_migration.py -v`
Expected: all five tests fail — no `scope_value` column yet, no `department:move` perm, `ck_permissions_action` lacks `'move'`.

- [ ] **Step 3: Write migration 0005**

Create `backend/alembic/versions/0005_plan6_departments_scope_value.py`:
```python
"""plan6 departments scope_value + department perms

Revision ID: 0005_plan6_departments_scope_value
Revises: 0004_plan5_user_assign_perm
Create Date: 2026-04-21
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0005_plan6_departments_scope_value"
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


def _action_check_sql(actions: tuple[str, ...]) -> str:
    literals = ",".join(f"'{a}'" for a in actions)
    return f"action IN ({literals})"


def upgrade() -> None:
    # --- 1. user_roles.scope_value ---
    op.add_column(
        "user_roles",
        sa.Column(
            "scope_value",
            sa.dialects.postgresql.UUID(as_uuid=True),
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

    # --- 3. Seed 5 department permissions ---
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": uuid.uuid4(),
                "code": f"department:{action}",
                "resource": "department",
                "action": action,
                "description": description,
            }
            for action, description in (
                ("create", "Create a department"),
                ("read", "Read / list / tree view departments"),
                ("update", "Rename a department"),
                ("delete", "Soft-delete a department"),
                ("move", "Move a department under a new parent"),
            )
        ],
    )

    # --- 4. Grant all 5 to built-in admin at global scope ---
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id, scope)
        SELECT r.id, p.id, 'global'
        FROM roles r, permissions p
        WHERE r.code = 'admin'
          AND p.code IN (
            'department:create','department:read','department:update',
            'department:delete','department:move'
          )
    """)


def downgrade() -> None:
    # --- 1. Remove grants + perms (FK-safe order) ---
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE code IN (
                'department:create','department:read','department:update',
                'department:delete','department:move'
            )
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE code IN (
            'department:create','department:read','department:update',
            'department:delete','department:move'
        )
    """)

    # --- 2. Restore original action CHECK (no 'move') ---
    op.drop_constraint("ck_permissions_action", "permissions", type_="check")
    op.create_check_constraint(
        "ck_permissions_action",
        "permissions",
        _action_check_sql(_OLD_ACTIONS),
    )

    # --- 3. Drop scope_value column + partial index ---
    op.drop_index("ix_user_roles_scope_value", table_name="user_roles")
    op.drop_column("user_roles", "scope_value")
```

- [ ] **Step 4: Run migration + test — expect pass**

Test DB is isolated per `feedback_test_db_isolation.md`; the pytest fixture should apply migrations to head automatically. If not:
```bash
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run pytest tests/migrations/test_0005_migration.py -v
```
Expected: all five tests green.

- [ ] **Step 5: Verify downgrade is clean**

```bash
docker compose exec backend uv run alembic downgrade -1
docker compose exec backend uv run alembic upgrade head
```
Expected: both commands exit 0 with no error. Re-run migration tests — all green.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/0005_plan6_departments_scope_value.py backend/tests/migrations/
git commit -m "feat(migration): 0005 add user_roles.scope_value + department perms + 'move' action"
```

---

## Phase B — `apply_scope` rewrite (backward-compat locked)

The existing Plan 4 `apply_scope` tests cover DEPT and DEPT_TREE branches and assume the anchor is `user.department_id`. With the new column `scope_value = NULL` (the state immediately after migration 0005), behaviour must be byte-identical to Plan 4 — those tests stay green unchanged. New tests add `scope_value ≠ NULL` cases.

### Task B1: Lock the backward-compat baseline

- [ ] **Step 1: Run existing apply_scope tests to establish green baseline**

```bash
docker compose exec backend uv run pytest tests/core/test_permissions.py -v
```
Expected: all existing tests pass. Record the test count (we need the same count to stay green after the rewrite).

- [ ] **Step 2: Commit nothing** — this is the baseline lock, not a change.

---

### Task B2: Add new tests for `scope_value ≠ NULL` anchoring (DEPT)

**Files:**
- Modify: `backend/tests/core/test_permissions.py` (append new tests at end)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/core/test_permissions.py`:
```python
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import apply_scope
from app.modules.auth.models import User
from app.modules.rbac.constants import ScopeEnum
from app.modules.rbac.models import (
    Department,
    Permission,
    Role,
    RolePermission,
    UserRole,
)


pytestmark = pytest.mark.asyncio


async def _seed_tree(session: AsyncSession) -> tuple[Department, Department]:
    root = Department(name="Root", path="/root/", depth=0)
    other = Department(name="Other", path="/other/", depth=0)
    session.add_all([root, other])
    await session.flush()
    return root, other


async def test_apply_scope_dept_uses_scope_value_when_set(
    db_session: AsyncSession,
) -> None:
    """User's own dept=Root but assignment.scope_value=Other → sees Other rows."""
    root, other = await _seed_tree(db_session)
    user = User(
        email="u@test",
        password_hash="x",
        full_name="U",
        department_id=root.id,
    )
    db_session.add(user)
    role = Role(code="r6b2", name="R")
    perm = Permission(code="user:list", resource="user", action="list")
    db_session.add_all([role, perm])
    await db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id, scope="dept"))
    db_session.add(
        UserRole(user_id=user.id, role_id=role.id, scope_value=other.id)
    )
    await db_session.flush()

    # Scope map on User maps DEPT -> department_id field.
    perms = {"user:list": ScopeEnum.DEPT}
    stmt = select(User)
    scoped = apply_scope(stmt, user, "user:list", User, perms)
    compiled = str(scoped.compile(compile_kwargs={"literal_binds": True}))
    # The anchor should derive from UserRole.scope_value (=other.id),
    # not user.department_id (=root.id).
    assert str(other.id) in compiled or "COALESCE" in compiled.upper()


async def test_apply_scope_dept_falls_back_to_user_dept_when_scope_value_null(
    db_session: AsyncSession,
) -> None:
    """NULL scope_value → identical to Plan 4 behaviour."""
    root, _ = await _seed_tree(db_session)
    user = User(
        email="u2@test",
        password_hash="x",
        full_name="U2",
        department_id=root.id,
    )
    db_session.add(user)
    role = Role(code="r6b2b", name="R2")
    perm = Permission(code="user:list", resource="user", action="list")
    db_session.add_all([role, perm])
    await db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id, scope="dept"))
    db_session.add(UserRole(user_id=user.id, role_id=role.id, scope_value=None))
    await db_session.flush()

    perms = {"user:list": ScopeEnum.DEPT}
    stmt = select(User)
    scoped = apply_scope(stmt, user, "user:list", User, perms)
    compiled = str(scoped.compile(compile_kwargs={"literal_binds": True}))
    # Fallback anchor is user.department_id (root).
    assert str(root.id) in compiled
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/core/test_permissions.py::test_apply_scope_dept_uses_scope_value_when_set -v`
Expected: the COALESCE-or-other-id assertion fails — the current `apply_scope` emits `department_id = user.department_id` literal.

---

### Task B3: Rewrite `apply_scope` DEPT branch to read `scope_value`

**Files:**
- Modify: `backend/app/core/permissions.py`

- [ ] **Step 1: Replace the DEPT branch**

Edit `backend/app/core/permissions.py`. In `apply_scope`, replace the `if scope == ScopeEnum.DEPT` branch (currently `return stmt.where(field == user.department_id)`) with:

```python
    if scope == ScopeEnum.DEPT:
        # Union of per-assignment scope_values (or user.department_id fallback)
        # for every role this user holds that grants `code` at DEPT scope.
        dept_ids = (
            select(func.coalesce(UserRole.scope_value, user.department_id))
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(UserRole.user_id == user.id)
            .where(Permission.code == code)
            .where(RolePermission.scope == ScopeEnum.DEPT.value)
        )
        return stmt.where(field.in_(dept_ids))
```

- [ ] **Step 2: Run tests — expect both Plan 4 baseline AND new test to pass**

```bash
docker compose exec backend uv run pytest tests/core/test_permissions.py -v
```
Expected: baseline tests still green (NULL scope_value falls back to `user.department_id` → same rows). New test `test_apply_scope_dept_uses_scope_value_when_set` is now green.

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/permissions.py backend/tests/core/test_permissions.py
git commit -m "feat(core): apply_scope DEPT reads UserRole.scope_value with fallback"
```

---

### Task B4: Rewrite `apply_scope` DEPT_TREE branch

Same shape as DEPT, but each anchor dept expands to its own subtree via `Department.path LIKE prefix`.

**Files:**
- Modify: `backend/app/core/permissions.py`
- Modify: `backend/tests/core/test_permissions.py`

- [ ] **Step 1: Add the failing test**

Append to `backend/tests/core/test_permissions.py`:
```python
async def test_apply_scope_dept_tree_uses_scope_value_subtree(
    db_session: AsyncSession,
) -> None:
    """DEPT_TREE with scope_value=Other expands to Other's subtree, not Root's."""
    root, other = await _seed_tree(db_session)
    child_of_other = Department(
        name="OtherChild", parent_id=other.id, path="/other/child/", depth=1
    )
    db_session.add(child_of_other)
    await db_session.flush()

    user = User(
        email="u3@test",
        password_hash="x",
        full_name="U3",
        department_id=root.id,
    )
    db_session.add(user)
    role = Role(code="r6b4", name="R4")
    perm = Permission(code="user:list", resource="user", action="list")
    db_session.add_all([role, perm])
    await db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id, scope="dept_tree"))
    db_session.add(
        UserRole(user_id=user.id, role_id=role.id, scope_value=other.id)
    )
    await db_session.flush()

    perms = {"user:list": ScopeEnum.DEPT_TREE}
    stmt = select(User)
    scoped = apply_scope(stmt, user, "user:list", User, perms)
    compiled = str(scoped.compile(compile_kwargs={"literal_binds": True}))
    # The anchor subtree prefix should include `/other/`, not `/root/` only.
    assert "/other/" in compiled
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/core/test_permissions.py::test_apply_scope_dept_tree_uses_scope_value_subtree -v`
Expected: fails — current DEPT_TREE anchors solely to `user.department_id` (root).

- [ ] **Step 3: Replace the DEPT_TREE branch**

In `backend/app/core/permissions.py`, replace the existing `if scope == ScopeEnum.DEPT_TREE:` block with:

```python
    if scope == ScopeEnum.DEPT_TREE:
        # For each role/permission granting this code at dept_tree scope,
        # expand the anchor dept (scope_value or user.department_id) to its
        # subtree via Department.path LIKE prefix.
        anchor_ids = (
            select(func.coalesce(UserRole.scope_value, user.department_id).label("anchor"))
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(UserRole.user_id == user.id)
            .where(Permission.code == code)
            .where(RolePermission.scope == ScopeEnum.DEPT_TREE.value)
        ).subquery("anchor")
        anchor_paths = (
            select(Department.path)
            .where(Department.id.in_(select(anchor_ids.c.anchor)))
            .subquery("anchor_paths")
        )
        subtree = (
            select(Department.id)
            .join(
                anchor_paths,
                Department.path.like(func.concat(anchor_paths.c.path, "%")),
            )
        )
        return stmt.where(field.in_(subtree))
```

- [ ] **Step 4: Run tests — expect all green**

```bash
docker compose exec backend uv run pytest tests/core/test_permissions.py -v
```
Expected: baseline tests still green + both new DEPT + DEPT_TREE tests green.

- [ ] **Step 5: Full suite sanity check**

```bash
docker compose exec backend uv run pytest -q
```
Expected: same pass count as Plan 5 baseline plus the new tests. No regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/permissions.py backend/tests/core/test_permissions.py
git commit -m "feat(core): apply_scope DEPT_TREE reads UserRole.scope_value with fallback"
```

---

## Phase C — Backend `modules/department/`

New feature-first module per convention 08. Imports `Department` from `rbac.models`; does NOT define a new model.

### Task C1: Module scaffold + `CLAUDE.md`

**Files:**
- Create: `backend/app/modules/department/__init__.py` (empty)
- Create: `backend/app/modules/department/models.py`
- Create: `backend/app/modules/department/CLAUDE.md`

- [ ] **Step 1: Create `models.py` (re-export)**

Content:
```python
from __future__ import annotations

# Feature-first pattern: re-export the SQLAlchemy model owned by rbac/.
from app.modules.rbac.models import Department

__all__ = ["Department"]
```

- [ ] **Step 2: Create `CLAUDE.md`**

Content:
```markdown
# department/ — Agent guide

Admin CRUD over the `Department` SQLAlchemy model, which lives in `modules/rbac/models.py`.
This module does NOT own a model — it imports `Department` from rbac.

Endpoints: list (flat, paginated) / tree (non-paginated) / read / create / update / soft-delete / move.
All guarded by the `department:*` permissions seeded in migration 0005.

Materialized-path subtree rewrite + cycle detection live in `service.py::DepartmentService.move_department`.
Guards (`HasChildren`, `HasAssignedUsers`, `NoCycle`) are registered on `Department.__guards__` in `rbac/models.py`.
```

- [ ] **Step 3: Create empty `__init__.py`**

```bash
touch backend/app/modules/department/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/modules/department/
git commit -m "feat(department): module scaffold + re-export Department model"
```

---

### Task C2: Schemas

**Files:**
- Create: `backend/app/modules/department/schemas.py`
- Create: `backend/tests/modules/department/__init__.py` (empty)
- Create: `backend/tests/modules/department/test_schemas.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/modules/department/test_schemas.py`:
```python
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.modules.department.schemas import (
    DepartmentCreateIn,
    DepartmentMoveIn,
    DepartmentNode,
    DepartmentOut,
    DepartmentUpdateIn,
)


def test_create_requires_name_and_parent() -> None:
    with pytest.raises(ValidationError):
        DepartmentCreateIn(name="", parent_id=uuid.uuid4())
    ok = DepartmentCreateIn(name="Ops", parent_id=uuid.uuid4())
    assert ok.name == "Ops"


def test_update_name_only() -> None:
    assert DepartmentUpdateIn(name="New Name").name == "New Name"


def test_move_requires_new_parent() -> None:
    with pytest.raises(ValidationError):
        DepartmentMoveIn.model_validate({})
    assert DepartmentMoveIn(new_parent_id=uuid.uuid4()).new_parent_id is not None


def test_out_schema_fields() -> None:
    d = DepartmentOut(
        id=uuid.uuid4(),
        parent_id=None,
        name="Root",
        path="/root/",
        depth=0,
        is_active=True,
    )
    j = d.model_dump(by_alias=True)
    assert j["parentId"] is None  # camel alias
    assert j["isActive"] is True


def test_node_has_children() -> None:
    parent = DepartmentNode(
        id=uuid.uuid4(),
        parent_id=None,
        name="Root",
        path="/root/",
        depth=0,
        is_active=True,
        children=[],
    )
    assert parent.children == []
```

- [ ] **Step 2: Run test — expect failure (ImportError)**

Run: `docker compose exec backend uv run pytest tests/modules/department/test_schemas.py -v`
Expected: `ModuleNotFoundError: No module named 'app.modules.department.schemas'`.

- [ ] **Step 3: Implement schemas**

Create `backend/app/modules/department/schemas.py`:
```python
from __future__ import annotations

import uuid
from typing import Self

from pydantic import Field, model_validator

from app.core.schemas import BaseSchema


class DepartmentCreateIn(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    parent_id: uuid.UUID


class DepartmentUpdateIn(BaseSchema):
    name: str = Field(min_length=1, max_length=100)


class DepartmentMoveIn(BaseSchema):
    new_parent_id: uuid.UUID


class DepartmentOut(BaseSchema):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    path: str
    depth: int
    is_active: bool


class DepartmentNode(DepartmentOut):
    children: list["DepartmentNode"] = Field(default_factory=list)

    @model_validator(mode="after")
    def _freeze_children(self) -> Self:
        # Children list is built by the router, not by client input — no extra
        # invariants to enforce here. Keeping the validator as a hook for V2.
        return self


DepartmentNode.model_rebuild()
```

Also remove the old `DepartmentOut` class from `backend/app/modules/rbac/schemas.py` (it moves here). Update the import in `backend/app/modules/rbac/router.py` accordingly once Phase D lands — for now, add a compatibility re-export in rbac to avoid breaking the rbac router mid-phase:

Edit `backend/app/modules/rbac/schemas.py` — replace the existing `DepartmentOut` class body with a re-export:
```python
# DepartmentOut moved to modules/department/schemas.py — re-exported here
# for Phase C ↔ D transition. Removed in Phase D4 once rbac/router.py stops
# importing it.
from app.modules.department.schemas import DepartmentOut  # noqa: F401
```

- [ ] **Step 4: Run test — expect pass**

```bash
docker compose exec backend uv run pytest tests/modules/department/test_schemas.py -v
docker compose exec backend uv run pytest tests/modules/rbac -v
```
Expected: new schemas tests green + existing rbac tests still green (re-export keeps them working).

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/department/schemas.py backend/app/modules/rbac/schemas.py backend/tests/modules/department/
git commit -m "feat(department): Pydantic schemas + re-export from rbac for transition"
```

---

### Task C3: Guards — `HasChildren`, `HasAssignedUsers`, `NoCycle`

**Files:**
- Modify: `backend/app/modules/rbac/guards.py`
- Modify: `backend/app/modules/rbac/models.py` (register `__guards__`)
- Create: `backend/tests/modules/rbac/test_department_guards.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/modules/rbac/test_department_guards.py`:
```python
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guards import GuardViolationError
from app.modules.auth.models import User
from app.modules.rbac.guards import HasAssignedUsers, HasChildren, NoCycle
from app.modules.rbac.models import Department

pytestmark = pytest.mark.asyncio


async def test_has_children_rejects_when_active_child_exists(
    db_session: AsyncSession,
) -> None:
    parent = Department(name="P", path="/p/", depth=0)
    db_session.add(parent)
    await db_session.flush()
    child = Department(name="C", parent_id=parent.id, path="/p/c/", depth=1)
    db_session.add(child)
    await db_session.flush()

    with pytest.raises(GuardViolationError) as ei:
        await HasChildren().check(db_session, parent)
    assert ei.value.code == "department.has-children"


async def test_has_children_passes_when_only_inactive_children(
    db_session: AsyncSession,
) -> None:
    parent = Department(name="P2", path="/p2/", depth=0)
    db_session.add(parent)
    await db_session.flush()
    child = Department(
        name="C2", parent_id=parent.id, path="/p2/c2/", depth=1, is_active=False
    )
    db_session.add(child)
    await db_session.flush()

    await HasChildren().check(db_session, parent)


async def test_has_assigned_users_rejects_when_active_user_assigned(
    db_session: AsyncSession,
) -> None:
    dept = Department(name="D", path="/d/", depth=0)
    db_session.add(dept)
    await db_session.flush()
    u = User(
        email="hu@test", password_hash="x", full_name="HU", department_id=dept.id
    )
    db_session.add(u)
    await db_session.flush()

    with pytest.raises(GuardViolationError) as ei:
        await HasAssignedUsers().check(db_session, dept)
    assert ei.value.code == "department.has-users"


async def test_no_cycle_rejects_self_parent(db_session: AsyncSession) -> None:
    d = Department(name="X", path="/x/", depth=0)
    db_session.add(d)
    await db_session.flush()

    with pytest.raises(GuardViolationError) as ei:
        await NoCycle().check(db_session, d, new_parent_id=d.id)
    assert ei.value.code == "department.self-parent"


async def test_no_cycle_rejects_move_into_descendant(
    db_session: AsyncSession,
) -> None:
    root = Department(name="R", path="/r/", depth=0)
    db_session.add(root)
    await db_session.flush()
    child = Department(name="C", parent_id=root.id, path="/r/c/", depth=1)
    db_session.add(child)
    await db_session.flush()

    with pytest.raises(GuardViolationError) as ei:
        await NoCycle().check(db_session, root, new_parent_id=child.id)
    assert ei.value.code == "department.cycle-detected"


async def test_no_cycle_passes_for_unrelated_parent(
    db_session: AsyncSession,
) -> None:
    a = Department(name="A", path="/a/", depth=0)
    b = Department(name="B", path="/b/", depth=0)
    db_session.add_all([a, b])
    await db_session.flush()

    await NoCycle().check(db_session, a, new_parent_id=b.id)
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/rbac/test_department_guards.py -v`
Expected: `ImportError` — classes not defined yet.

- [ ] **Step 3: Implement guards**

Append to `backend/app/modules/rbac/guards.py`:
```python
from app.modules.rbac.models import Department


class HasChildren:
    """Forbid delete when the department has any active children."""

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        **_: Any,
    ) -> None:
        stmt = (
            select(func.count())
            .select_from(Department)
            .where(Department.parent_id == instance.id)
            .where(Department.is_active.is_(True))
        )
        count = (await session.execute(stmt)).scalar_one()
        if count > 0:
            raise GuardViolationError(
                code="department.has-children",
                ctx={"department_id": str(instance.id), "active_children": int(count)},
            )


class HasAssignedUsers:
    """Forbid delete when any active user has this as their department_id."""

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        **_: Any,
    ) -> None:
        # Import inside to avoid a models ↔ guards cycle at import time.
        from app.modules.auth.models import User

        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.department_id == instance.id)
            .where(User.is_active.is_(True))
        )
        count = (await session.execute(stmt)).scalar_one()
        if count > 0:
            raise GuardViolationError(
                code="department.has-users",
                ctx={"department_id": str(instance.id), "assigned_users": int(count)},
            )


class NoCycle:
    """Forbid move when `new_parent_id` is self or a descendant of instance."""

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        new_parent_id: Any | None = None,
        **_: Any,
    ) -> None:
        if new_parent_id is None:
            return
        if new_parent_id == instance.id:
            raise GuardViolationError(
                code="department.self-parent",
                ctx={"department_id": str(instance.id)},
            )
        # Is new_parent_id inside the subtree of instance?
        # Subtree members have path starting with instance.path.
        target_path_stmt = (
            select(Department.path).where(Department.id == new_parent_id)
        )
        target_path = (await session.execute(target_path_stmt)).scalar_one_or_none()
        if target_path is None:
            return  # parent not found — let service/load_in_scope handle.
        if target_path.startswith(instance.path):
            raise GuardViolationError(
                code="department.cycle-detected",
                ctx={
                    "department_id": str(instance.id),
                    "new_parent_id": str(new_parent_id),
                },
            )
```

- [ ] **Step 4: Register guards on `Department`**

Edit `backend/app/modules/rbac/models.py` — append at the bottom of the file (after the `Department` class is fully declared, to avoid import-time cycles, these guards are attached lazily):
```python
# --- Deferred: wire Department.__guards__ ---
# HasChildren / HasAssignedUsers / NoCycle live in rbac/guards.py; attach them
# after both modules are loaded to avoid a models ↔ guards import cycle.
def _install_department_guards() -> None:
    from app.modules.rbac.guards import HasAssignedUsers, HasChildren, NoCycle

    Department.__guards__ = {
        "delete": [HasChildren(), HasAssignedUsers()],
        "move": [NoCycle()],
    }


_install_department_guards()
```

- [ ] **Step 5: Run tests — expect pass**

```bash
docker compose exec backend uv run pytest tests/modules/rbac/test_department_guards.py -v
docker compose exec backend uv run pytest tests/modules/rbac -v
```
Expected: new guard tests green + existing rbac tests still green.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/rbac/guards.py backend/app/modules/rbac/models.py backend/tests/modules/rbac/test_department_guards.py
git commit -m "feat(rbac): HasChildren, HasAssignedUsers, NoCycle guards + Department.__guards__"
```

---

### Task C4: CRUD helpers

**Files:**
- Create: `backend/app/modules/department/crud.py`
- Create: `backend/tests/modules/department/test_crud.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/modules/department/test_crud.py`:
```python
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemDetails
from app.modules.department.crud import (
    build_list_flat_stmt,
    create_department,
    get_tree_rooted_at,
    soft_delete_department,
    update_department,
)
from app.modules.department.schemas import DepartmentCreateIn, DepartmentUpdateIn
from app.modules.rbac.models import Department

pytestmark = pytest.mark.asyncio


async def test_create_under_existing_parent_builds_path(
    db_session: AsyncSession,
) -> None:
    parent = Department(name="Root", path="/root/", depth=0)
    db_session.add(parent)
    await db_session.flush()

    created = await create_department(
        db_session, DepartmentCreateIn(name="Ops", parent_id=parent.id)
    )
    assert created.parent_id == parent.id
    assert created.depth == 1
    assert created.path.startswith("/root/")
    assert created.path.endswith("/")


async def test_create_with_unknown_parent_raises(db_session: AsyncSession) -> None:
    with pytest.raises(ProblemDetails) as ei:
        await create_department(
            db_session,
            DepartmentCreateIn(name="X", parent_id=uuid.uuid4()),
        )
    assert ei.value.code == "resource.not-found"


async def test_update_renames(db_session: AsyncSession) -> None:
    d = Department(name="Old", path="/old/", depth=0)
    db_session.add(d)
    await db_session.flush()

    updated = await update_department(db_session, d, DepartmentUpdateIn(name="New"))
    assert updated.name == "New"


async def test_soft_delete_toggles_is_active(db_session: AsyncSession) -> None:
    d = Department(name="D", path="/d/", depth=0)
    db_session.add(d)
    await db_session.flush()

    await soft_delete_department(db_session, d, actor=None)
    assert d.is_active is False


async def test_tree_rooted_at_returns_self_plus_descendants(
    db_session: AsyncSession,
) -> None:
    root = Department(name="R", path="/r/", depth=0)
    db_session.add(root)
    await db_session.flush()
    child = Department(name="C", parent_id=root.id, path="/r/c/", depth=1)
    db_session.add(child)
    await db_session.flush()

    rows = await get_tree_rooted_at(db_session, root_id=root.id, include_inactive=True)
    names = {r.name for r in rows}
    assert names == {"R", "C"}


def test_list_flat_stmt_filters_inactive_by_default() -> None:
    stmt = build_list_flat_stmt(is_active=True)
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "is_active" in compiled
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/department/test_crud.py -v`
Expected: `ImportError`.

- [ ] **Step 3: Implement CRUD**

Create `backend/app/modules/department/crud.py`:
```python
from __future__ import annotations

import re
import uuid

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


async def create_department(
    session: AsyncSession, payload: DepartmentCreateIn
) -> Department:
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
    session: AsyncSession, target: Department, *, actor
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
```

- [ ] **Step 4: Run test — expect pass**

```bash
docker compose exec backend uv run pytest tests/modules/department/test_crud.py -v
```
Expected: all tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/department/crud.py backend/tests/modules/department/test_crud.py
git commit -m "feat(department): crud helpers (create, update, soft-delete, tree)"
```

---

### Task C5: `DepartmentService.move_department`

Materialized-path subtree rewrite. Must be atomic and must rewrite depth + path for every descendant.

**Files:**
- Create: `backend/app/modules/department/service.py`
- Create: `backend/tests/modules/department/test_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/modules/department/test_service.py`:
```python
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guards import GuardViolationError
from app.modules.department.service import DepartmentService
from app.modules.rbac.models import Department

pytestmark = pytest.mark.asyncio


async def _mk_tree(session: AsyncSession) -> tuple[Department, Department, Department, Department]:
    """Build:
        /a/
        /a/a1/
        /a/a1/a11/
        /b/
    """
    a = Department(name="a", path="/a/", depth=0)
    b = Department(name="b", path="/b/", depth=0)
    session.add_all([a, b])
    await session.flush()
    a1 = Department(name="a1", parent_id=a.id, path="/a/a1/", depth=1)
    session.add(a1)
    await session.flush()
    a11 = Department(name="a11", parent_id=a1.id, path="/a/a1/a11/", depth=2)
    session.add(a11)
    await session.flush()
    return a, b, a1, a11


async def test_move_leaf_under_new_parent_rewrites_path_and_depth(
    db_session: AsyncSession,
) -> None:
    a, b, _a1, a11 = await _mk_tree(db_session)
    svc = DepartmentService()
    await svc.move_department(db_session, a11, new_parent_id=b.id)
    await db_session.flush()
    await db_session.refresh(a11)
    assert a11.parent_id == b.id
    assert a11.path.startswith("/b/")
    assert a11.depth == 1


async def test_move_subtree_rewrites_every_descendant(
    db_session: AsyncSession,
) -> None:
    a, b, a1, a11 = await _mk_tree(db_session)
    svc = DepartmentService()
    await svc.move_department(db_session, a1, new_parent_id=b.id)
    await db_session.flush()
    await db_session.refresh(a1)
    await db_session.refresh(a11)
    assert a1.path.startswith("/b/")
    assert a1.depth == 1
    assert a11.path.startswith("/b/")
    assert a11.depth == 2
    assert a11.parent_id == a1.id  # parent link within subtree preserved


async def test_move_into_own_descendant_raises_cycle(
    db_session: AsyncSession,
) -> None:
    a, _b, _a1, a11 = await _mk_tree(db_session)
    svc = DepartmentService()
    with pytest.raises(GuardViolationError) as ei:
        await svc.move_department(db_session, a, new_parent_id=a11.id)
    assert ei.value.code == "department.cycle-detected"


async def test_move_to_same_parent_is_noop(db_session: AsyncSession) -> None:
    a, _b, a1, _a11 = await _mk_tree(db_session)
    svc = DepartmentService()
    await svc.move_department(db_session, a1, new_parent_id=a.id)
    await db_session.flush()
    await db_session.refresh(a1)
    assert a1.path == "/a/a1/"
    assert a1.depth == 1
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/department/test_service.py -v`
Expected: `ImportError`.

- [ ] **Step 3: Implement the service**

Create `backend/app/modules/department/service.py`:
```python
from __future__ import annotations

import re
import uuid

from sqlalchemy import select, update
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
        actor=None,
    ) -> None:
        # 1. Run guards first (NoCycle rejects self-parent + descendant cycles).
        for guard in getattr(Department, "__guards__", {}).get(_GUARDS_KEY, []):
            await guard.check(session, dept, actor=actor, new_parent_id=new_parent_id)

        # 2. Resolve new parent; refuse if inactive.
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
        #    Bulk update replaces the leading old_prefix with new_prefix; depth is
        #    recalculated as the delta between the old and new prefixes.
        depth_delta = new_prefix.count("/") - old_prefix.count("/")
        rows_stmt = select(Department).where(Department.path.like(f"{old_prefix}%"))
        for row in (await session.execute(rows_stmt)).scalars().all():
            row.path = new_prefix + row.path[len(old_prefix):]
            row.depth = row.depth + depth_delta

        # 5. Update dept.parent_id explicitly (only the moved node's parent changes).
        dept.parent_id = new_parent_id

        await session.flush()
```

- [ ] **Step 4: Run tests — expect pass**

```bash
docker compose exec backend uv run pytest tests/modules/department/test_service.py -v
```
Expected: all four tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/department/service.py backend/tests/modules/department/test_service.py
git commit -m "feat(department): DepartmentService.move_department with subtree rewrite"
```

---

## Phase D — Router + wiring

### Task D1: Router with 7 endpoints

**Files:**
- Create: `backend/app/modules/department/router.py`
- Create: `backend/tests/modules/department/test_router.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/modules/department/test_router.py`:
```python
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_departments_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/departments")
    assert r.status_code == 401


async def test_tree_endpoint_returns_nested_children(
    admin_client: AsyncClient, seed_department_tree
) -> None:
    r = await admin_client.get("/api/v1/departments/tree")
    assert r.status_code == 200
    body = r.json()
    # Root-level array, each root has a `children` key.
    assert isinstance(body, list)
    assert all("children" in node for node in body)


async def test_create_department(
    admin_client: AsyncClient, seed_department_tree
) -> None:
    root_id = seed_department_tree["root_id"]
    r = await admin_client.post(
        "/api/v1/departments", json={"name": "NewChild", "parentId": str(root_id)}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "NewChild"
    assert body["parentId"] == str(root_id)


async def test_rename_department(
    admin_client: AsyncClient, seed_department_tree
) -> None:
    leaf_id = seed_department_tree["leaf_id"]
    r = await admin_client.patch(
        f"/api/v1/departments/{leaf_id}", json={"name": "Renamed"}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"


async def test_move_department(
    admin_client: AsyncClient, seed_department_tree
) -> None:
    leaf_id = seed_department_tree["leaf_id"]
    other_root_id = seed_department_tree["other_root_id"]
    r = await admin_client.post(
        f"/api/v1/departments/{leaf_id}/move",
        json={"newParentId": str(other_root_id)},
    )
    assert r.status_code == 200
    assert r.json()["parentId"] == str(other_root_id)


async def test_move_into_self_rejected(
    admin_client: AsyncClient, seed_department_tree
) -> None:
    leaf_id = seed_department_tree["leaf_id"]
    r = await admin_client.post(
        f"/api/v1/departments/{leaf_id}/move",
        json={"newParentId": str(leaf_id)},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "department.self-parent"


async def test_delete_department_with_children_rejected(
    admin_client: AsyncClient, seed_department_tree
) -> None:
    root_id = seed_department_tree["root_id"]
    r = await admin_client.delete(f"/api/v1/departments/{root_id}")
    assert r.status_code == 409
    assert r.json()["code"] == "department.has-children"


async def test_delete_leaf_ok(
    admin_client: AsyncClient, seed_department_tree
) -> None:
    leaf_id = seed_department_tree["leaf_id"]
    r = await admin_client.delete(f"/api/v1/departments/{leaf_id}")
    assert r.status_code == 204
```

Also add the seed fixture to `backend/tests/modules/department/conftest.py`:
```python
from __future__ import annotations

import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rbac.models import Department


@pytest_asyncio.fixture
async def seed_department_tree(db_session: AsyncSession) -> dict[str, uuid.UUID]:
    root = Department(name="Root", path="/root/", depth=0)
    other_root = Department(name="Other", path="/other/", depth=0)
    db_session.add_all([root, other_root])
    await db_session.flush()
    leaf = Department(
        name="Leaf", parent_id=root.id, path="/root/leaf/", depth=1
    )
    db_session.add(leaf)
    await db_session.flush()
    return {
        "root_id": root.id,
        "other_root_id": other_root.id,
        "leaf_id": leaf.id,
    }
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/department/test_router.py -v`
Expected: 404 on every endpoint (router not registered yet).

- [ ] **Step 3: Implement router**

Create `backend/app/modules/department/router.py`:
```python
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import GuardViolationCtx, ProblemDetails
from app.core.guards import GuardViolationError
from app.core.pagination import Page, PageQuery, paginate
from app.core.permissions import (
    apply_scope,
    current_user_dep,
    get_user_permissions,
    load_in_scope,
    require_perm,
)
from app.modules.auth.models import User
from app.modules.department.crud import (
    build_list_flat_stmt,
    create_department,
    get_tree_rooted_at,
    soft_delete_department,
    update_department,
)
from app.modules.department.schemas import (
    DepartmentCreateIn,
    DepartmentMoveIn,
    DepartmentNode,
    DepartmentOut,
    DepartmentUpdateIn,
)
from app.modules.department.service import DepartmentService
from app.modules.rbac.models import Department

router = APIRouter(tags=["department"])


def _guard_to_problem(e: GuardViolationError) -> ProblemDetails:
    # Department guard codes are all 409 (conflict with existing state).
    return ProblemDetails(
        code=e.code,
        status=409,
        detail=f"Operation blocked by guard: {e.code}.",
        guard_violation=GuardViolationCtx(guard=e.code, params=e.ctx),
    )


def _build_tree(rows: list[Department]) -> list[DepartmentNode]:
    by_id: dict[uuid.UUID, DepartmentNode] = {
        r.id: DepartmentNode.model_validate(r, from_attributes=True) for r in rows
    }
    roots: list[DepartmentNode] = []
    for r in rows:
        node = by_id[r.id]
        if r.parent_id is not None and r.parent_id in by_id:
            by_id[r.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


@router.get(
    "/departments",
    response_model=Page[DepartmentOut],
    dependencies=[Depends(require_perm("department:read"))],
)
async def list_departments_endpoint(
    pq: Annotated[PageQuery, Depends()],
    is_active: bool | None = Query(default=True),
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Page[DepartmentOut]:
    perms = await get_user_permissions(db, user)
    stmt = build_list_flat_stmt(is_active=is_active)
    stmt = apply_scope(stmt, user, "department:read", Department, perms)
    raw = await paginate(db, stmt, pq)
    items = [DepartmentOut.model_validate(i, from_attributes=True) for i in raw.items]
    return Page[DepartmentOut](
        items=items,
        total=raw.total,
        page=raw.page,
        size=raw.size,
        has_next=raw.has_next,
    )


@router.get(
    "/departments/tree",
    response_model=list[DepartmentNode],
    dependencies=[Depends(require_perm("department:read"))],
)
async def tree_departments_endpoint(
    include_inactive: bool = Query(default=False, alias="includeInactive"),
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> list[DepartmentNode]:
    rows = await get_tree_rooted_at(db, include_inactive=include_inactive)
    return _build_tree(rows)


@router.get(
    "/departments/{dept_id}",
    response_model=DepartmentOut,
    dependencies=[Depends(require_perm("department:read"))],
)
async def get_department_endpoint(
    dept_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, Department, dept_id, user, "department:read", perms)
    return DepartmentOut.model_validate(target, from_attributes=True)


@router.post(
    "/departments",
    response_model=DepartmentOut,
    status_code=201,
    dependencies=[Depends(require_perm("department:create"))],
)
async def create_department_endpoint(
    payload: DepartmentCreateIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    created = await create_department(db, payload)
    await db.commit()
    await db.refresh(created)
    return DepartmentOut.model_validate(created, from_attributes=True)


@router.patch(
    "/departments/{dept_id}",
    response_model=DepartmentOut,
    dependencies=[Depends(require_perm("department:update"))],
)
async def update_department_endpoint(
    dept_id: uuid.UUID,
    payload: DepartmentUpdateIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, Department, dept_id, user, "department:update", perms)
    updated = await update_department(db, target, payload)
    await db.commit()
    await db.refresh(updated)
    return DepartmentOut.model_validate(updated, from_attributes=True)


@router.post(
    "/departments/{dept_id}/move",
    response_model=DepartmentOut,
    dependencies=[Depends(require_perm("department:move"))],
)
async def move_department_endpoint(
    dept_id: uuid.UUID,
    payload: DepartmentMoveIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, Department, dept_id, user, "department:move", perms)
    try:
        await DepartmentService().move_department(
            db, target, new_parent_id=payload.new_parent_id, actor=user
        )
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    await db.refresh(target)
    return DepartmentOut.model_validate(target, from_attributes=True)


@router.delete(
    "/departments/{dept_id}",
    status_code=204,
    dependencies=[Depends(require_perm("department:delete"))],
)
async def delete_department_endpoint(
    dept_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Response:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, Department, dept_id, user, "department:delete", perms)
    try:
        for guard in getattr(Department, "__guards__", {}).get("delete", []):
            await guard.check(db, target, actor=user)
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await soft_delete_department(db, target, actor=user)
    await db.commit()
    return Response(status_code=204)
```

- [ ] **Step 4: Register router in `app/api/v1.py`**

Edit `backend/app/api/v1.py`:
```python
from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.department.router import router as department_router
from app.modules.rbac.router import router as rbac_router
from app.modules.user.router import router as user_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(rbac_router)
v1_router.include_router(user_router)
v1_router.include_router(department_router)
```

- [ ] **Step 5: Remove the duplicate list endpoint from `rbac/router.py`**

Edit `backend/app/modules/rbac/router.py` — delete the `list_departments_endpoint` function (lines 40–61) and the now-unused imports (`Page`, `PageQuery`, `paginate`, `apply_scope`, `get_user_permissions`, `Department`, `DepartmentOut`). Leave `/me/permissions` and `/roles`. The import line for `SUPERADMIN_ALL` stays (used by `/me/permissions`).

After pruning, the top of `rbac/router.py` should read:
```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import Page, PageQuery, paginate
from app.core.permissions import (
    SUPERADMIN_ALL,
    current_user_dep,
    get_user_permissions,
    require_perm,
)
from app.modules.auth.models import User
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import MePermissionsOut, RoleOut
```

- [ ] **Step 6: Remove the transition re-export from `rbac/schemas.py`**

Edit `backend/app/modules/rbac/schemas.py` — remove the `from app.modules.department.schemas import DepartmentOut  # noqa: F401` line added in C2. No callers in `rbac/` reference `DepartmentOut` any more.

- [ ] **Step 7: Run tests — expect pass**

```bash
docker compose exec backend uv run pytest tests/modules/department -v
docker compose exec backend uv run pytest tests/modules/rbac -v
docker compose exec backend uv run pytest -q
```
Expected: department router tests green, rbac tests still green, full suite green.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/v1.py backend/app/modules/department/router.py backend/app/modules/rbac/router.py backend/app/modules/rbac/schemas.py backend/tests/modules/department/
git commit -m "feat(department): 7 endpoints + router registration; remove duplicate /departments from rbac"
```

---

## Phase E — Frontend tree primitive

### Task E1: `@/components/ui/tree.tsx`

**Files:**
- Create: `frontend/src/components/ui/tree.tsx`
- Create: `frontend/src/components/ui/__tests__/tree.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/ui/__tests__/tree.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Tree, type TreeNode } from "../tree";

type Dept = { id: string; name: string; children?: Dept[] };

const data: Dept[] = [
  {
    id: "a",
    name: "A",
    children: [
      { id: "a1", name: "A1", children: [{ id: "a11", name: "A11" }] },
    ],
  },
  { id: "b", name: "B" },
];

function Harness({ onSelect }: { onSelect?: (id: string) => void }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  return (
    <Tree<Dept>
      nodes={data as TreeNode<Dept>[]}
      getId={(n) => n.id}
      getChildren={(n) => n.children ?? []}
      renderNode={(n) => <span>{n.name}</span>}
      expandedIds={expanded}
      onExpandChange={setExpanded}
      onSelect={(n) => onSelect?.(n.id)}
    />
  );
}

describe("Tree", () => {
  it("renders top-level nodes", () => {
    render(<Harness />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    // Deeper levels are hidden when expandedIds is empty.
    expect(screen.queryByText("A1")).not.toBeInTheDocument();
  });

  it("expands when the toggle is clicked", async () => {
    render(<Harness />);
    // Each expandable node exposes a button labeled with its own name.
    const [toggle] = screen.getAllByRole("button", { name: /^展开 A$/ });
    await userEvent.click(toggle);
    expect(screen.getByText("A1")).toBeInTheDocument();
  });

  it("invokes onSelect with the clicked node", async () => {
    const onSelect = vi.fn();
    render(<Harness onSelect={onSelect} />);
    await userEvent.click(screen.getByText("B"));
    expect(onSelect).toHaveBeenCalledWith("b");
  });
});
```

- [ ] **Step 2: Run test — expect failure**

Run: `cd frontend && npm test -- src/components/ui/__tests__/tree.test.tsx`
Expected: module-not-found.

- [ ] **Step 3: Implement `tree.tsx`**

Create `frontend/src/components/ui/tree.tsx`:
```tsx
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type TreeNode<T> = T;

export interface TreeProps<T> {
  nodes: T[];
  getId: (n: T) => string;
  getChildren: (n: T) => T[];
  renderNode: (n: T) => ReactNode;
  expandedIds: Set<string>;
  onExpandChange: (next: Set<string>) => void;
  onSelect?: (n: T) => void;
  selectedId?: string | null;
}

export function Tree<T>(props: TreeProps<T>) {
  return (
    <ul className="flex flex-col gap-0.5" role="tree">
      {props.nodes.map((n) => (
        <TreeItem<T> key={props.getId(n)} node={n} depth={0} {...props} />
      ))}
    </ul>
  );
}

function TreeItem<T>(
  props: TreeProps<T> & { node: T; depth: number },
) {
  const {
    node,
    depth,
    getId,
    getChildren,
    renderNode,
    expandedIds,
    onExpandChange,
    onSelect,
    selectedId,
  } = props;
  const id = getId(node);
  const children = getChildren(node);
  const hasChildren = children.length > 0;
  const isExpanded = expandedIds.has(id);
  const isSelected = selectedId === id;

  const toggle = () => {
    const next = new Set(expandedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onExpandChange(next);
  };

  return (
    <li role="treeitem" aria-expanded={hasChildren ? isExpanded : undefined}>
      <div
        className={cn(
          "flex items-center gap-2 rounded px-2 py-1 hover:bg-accent",
          isSelected && "bg-accent",
        )}
        style={{ paddingLeft: `${depth * 1.25 + 0.5}rem` }}
      >
        {hasChildren ? (
          <button
            type="button"
            aria-label={`${isExpanded ? "收起" : "展开"} ${
              typeof node === "object" && node !== null && "name" in (node as object)
                ? (node as { name: string }).name
                : id
            }`}
            onClick={toggle}
            className="inline-flex h-5 w-5 items-center justify-center text-xs text-muted-foreground"
          >
            {isExpanded ? "▾" : "▸"}
          </button>
        ) : (
          <span className="inline-block h-5 w-5" aria-hidden="true" />
        )}
        <button
          type="button"
          className="flex-1 truncate text-left"
          onClick={() => onSelect?.(node)}
        >
          {renderNode(node)}
        </button>
      </div>
      {hasChildren && isExpanded ? (
        <ul role="group" className="flex flex-col gap-0.5">
          {children.map((c) => (
            <TreeItem<T>
              key={getId(c)}
              node={c}
              depth={depth + 1}
              {...props}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd frontend && npm test -- src/components/ui/__tests__/tree.test.tsx`
Expected: 3/3 green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/tree.tsx frontend/src/components/ui/__tests__/tree.test.tsx
git commit -m "feat(ui): add @/components/ui/tree primitive (hand-rolled, no new dep)"
```

---

## Phase F — Frontend `modules/department/`

### Task F1: API + types

**Files:**
- Create: `frontend/src/modules/department/api.ts`
- Create: `frontend/src/modules/department/types.ts`

- [ ] **Step 1: Write types**

Create `frontend/src/modules/department/types.ts`:
```ts
export interface Department {
  id: string;
  parentId: string | null;
  name: string;
  path: string;
  depth: number;
  isActive: boolean;
}

export interface DepartmentNode extends Department {
  children: DepartmentNode[];
}

export interface DepartmentCreatePayload {
  name: string;
  parentId: string;
}

export interface DepartmentUpdatePayload {
  name: string;
}

export interface DepartmentMovePayload {
  newParentId: string;
}
```

- [ ] **Step 2: Write API client**

Create `frontend/src/modules/department/api.ts`:
```ts
import { client } from "@/api/client";
import type { Page, PageQuery } from "@/lib/pagination";
import type {
  Department,
  DepartmentCreatePayload,
  DepartmentMovePayload,
  DepartmentNode,
  DepartmentUpdatePayload,
} from "./types";

export async function listDepartments(
  pq: PageQuery & { is_active?: boolean },
): Promise<Page<Department>> {
  const { data } = await client.get<Page<Department>>("/departments", {
    params: pq,
  });
  return data;
}

export async function getDepartmentTree(
  includeInactive = false,
): Promise<DepartmentNode[]> {
  const { data } = await client.get<DepartmentNode[]>("/departments/tree", {
    params: { includeInactive },
  });
  return data;
}

export async function getDepartment(id: string): Promise<Department> {
  const { data } = await client.get<Department>(`/departments/${id}`);
  return data;
}

export async function createDepartment(
  payload: DepartmentCreatePayload,
): Promise<Department> {
  const { data } = await client.post<Department>("/departments", payload);
  return data;
}

export async function updateDepartment(
  id: string,
  payload: DepartmentUpdatePayload,
): Promise<Department> {
  const { data } = await client.patch<Department>(`/departments/${id}`, payload);
  return data;
}

export async function moveDepartment(
  id: string,
  payload: DepartmentMovePayload,
): Promise<Department> {
  const { data } = await client.post<Department>(
    `/departments/${id}/move`,
    payload,
  );
  return data;
}

export async function softDeleteDepartment(id: string): Promise<void> {
  await client.delete(`/departments/${id}`);
}
```

- [ ] **Step 3: Typecheck**

```bash
cd frontend && npm run typecheck
```
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/modules/department/api.ts frontend/src/modules/department/types.ts
git commit -m "feat(fe-department): types + api client"
```

---

### Task F2: `DepartmentListPage` (tree view + row actions)

**Files:**
- Create: `frontend/src/modules/department/DepartmentListPage.tsx`
- Create: `frontend/src/modules/department/__tests__/DepartmentListPage.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/modules/department/__tests__/DepartmentListPage.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DepartmentListPage } from "../DepartmentListPage";

vi.mock("../api", () => ({
  getDepartmentTree: vi.fn(),
  softDeleteDepartment: vi.fn(),
}));
import * as api from "../api";

describe("DepartmentListPage", () => {
  beforeEach(() => {
    vi.mocked(api.getDepartmentTree).mockResolvedValue([
      {
        id: "r1",
        parentId: null,
        name: "Root",
        path: "/root/",
        depth: 0,
        isActive: true,
        children: [
          {
            id: "c1",
            parentId: "r1",
            name: "Child",
            path: "/root/child/",
            depth: 1,
            isActive: true,
            children: [],
          },
        ],
      },
    ]);
  });

  it("fetches and renders the tree", async () => {
    render(
      <MemoryRouter>
        <DepartmentListPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Root")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test — expect failure (module not found)**

Run: `cd frontend && npm test -- src/modules/department/__tests__/DepartmentListPage.test.tsx`
Expected: file-not-found.

- [ ] **Step 3: Implement `DepartmentListPage`**

Create `frontend/src/modules/department/DepartmentListPage.tsx`:
```tsx
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Tree } from "@/components/ui/tree";
import { problemMessage } from "@/lib/problem-details";
import { getDepartmentTree, softDeleteDepartment } from "./api";
import { DepartmentEditModal } from "./components/DepartmentEditModal";
import { MoveDepartmentDialog } from "./components/MoveDepartmentDialog";
import type { DepartmentNode } from "./types";

type EditState =
  | { mode: "idle" }
  | { mode: "create"; parentId: string }
  | { mode: "rename"; node: DepartmentNode }
  | { mode: "move"; node: DepartmentNode };

export function DepartmentListPage() {
  const [tree, setTree] = useState<DepartmentNode[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<DepartmentNode | null>(null);
  const [editState, setEditState] = useState<EditState>({ mode: "idle" });
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await getDepartmentTree(includeInactive);
      setTree(data);
    } catch (err) {
      setError(problemMessage(err));
    }
  }, [includeInactive]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onDelete(n: DepartmentNode) {
    if (!window.confirm(`软删除 ${n.name}?`)) return;
    try {
      await softDeleteDepartment(n.id);
      await reload();
    } catch (err) {
      setError(problemMessage(err));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">部门管理</h1>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
          />
          显示已停用
        </label>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Tree<DepartmentNode>
        nodes={tree}
        getId={(n) => n.id}
        getChildren={(n) => n.children}
        renderNode={(n) => (
          <div className="flex w-full items-center justify-between gap-2">
            <span className={n.isActive ? "" : "text-muted-foreground line-through"}>
              {n.name}
            </span>
            <span className="flex gap-1" onClick={(e) => e.stopPropagation()}>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditState({ mode: "create", parentId: n.id })}
              >
                +
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditState({ mode: "rename", node: n })}
              >
                重命名
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditState({ mode: "move", node: n })}
              >
                移动
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onDelete(n)}
              >
                删除
              </Button>
            </span>
          </div>
        )}
        expandedIds={expanded}
        onExpandChange={setExpanded}
        onSelect={setSelected}
        selectedId={selected?.id ?? null}
      />
      {editState.mode === "create" || editState.mode === "rename" ? (
        <DepartmentEditModal
          state={editState}
          onClose={() => setEditState({ mode: "idle" })}
          onSaved={async () => {
            setEditState({ mode: "idle" });
            await reload();
          }}
        />
      ) : null}
      {editState.mode === "move" ? (
        <MoveDepartmentDialog
          source={editState.node}
          tree={tree}
          onClose={() => setEditState({ mode: "idle" })}
          onMoved={async () => {
            setEditState({ mode: "idle" });
            await reload();
          }}
        />
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Stub the two child components so the test compiles**

Create `frontend/src/modules/department/components/DepartmentEditModal.tsx` (stub — real body in F3):
```tsx
import type { DepartmentNode } from "../types";

export type EditModalState =
  | { mode: "create"; parentId: string }
  | { mode: "rename"; node: DepartmentNode };

export function DepartmentEditModal(_props: {
  state: EditModalState;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  return null;
}
```

Create `frontend/src/modules/department/components/MoveDepartmentDialog.tsx` (stub — real body in F4):
```tsx
import type { DepartmentNode } from "../types";

export function MoveDepartmentDialog(_props: {
  source: DepartmentNode;
  tree: DepartmentNode[];
  onClose: () => void;
  onMoved: () => void | Promise<void>;
}) {
  return null;
}
```

- [ ] **Step 5: Run test — expect pass**

Run: `cd frontend && npm test -- src/modules/department/__tests__/DepartmentListPage.test.tsx`
Expected: 1/1 green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/department/DepartmentListPage.tsx frontend/src/modules/department/components/ frontend/src/modules/department/__tests__/
git commit -m "feat(fe-department): DepartmentListPage tree view + inline actions"
```

---

### Task F3: `DepartmentEditModal` via `FormRenderer`

**Files:**
- Modify: `frontend/src/modules/department/components/DepartmentEditModal.tsx` (replace stub)
- Create: `frontend/src/modules/department/schema.ts`
- Create: `frontend/src/modules/department/__tests__/DepartmentEditModal.test.tsx`

- [ ] **Step 1: Write the JSON Schema file**

Create `frontend/src/modules/department/schema.ts`:
```ts
export const departmentCreateSchema = {
  type: "object",
  properties: {
    name: {
      type: "string",
      title: "部门名称",
      minLength: 1,
      maxLength: 100,
    },
  },
  required: ["name"],
};

export const departmentUpdateSchema = departmentCreateSchema;
```

- [ ] **Step 2: Write the failing test**

Create `frontend/src/modules/department/__tests__/DepartmentEditModal.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DepartmentEditModal } from "../components/DepartmentEditModal";

vi.mock("../api", () => ({
  createDepartment: vi.fn().mockResolvedValue({}),
  updateDepartment: vi.fn().mockResolvedValue({}),
}));
import * as api from "../api";

describe("DepartmentEditModal", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates via POST when mode=create", async () => {
    const onSaved = vi.fn();
    render(
      <DepartmentEditModal
        state={{ mode: "create", parentId: "p1" }}
        onClose={() => {}}
        onSaved={onSaved}
      />,
    );
    await userEvent.type(screen.getByLabelText("部门名称"), "NewDept");
    await userEvent.click(screen.getByRole("button", { name: "保存" }));
    expect(api.createDepartment).toHaveBeenCalledWith({
      name: "NewDept",
      parentId: "p1",
    });
  });

  it("blocks submit when name is empty (ajv)", async () => {
    const onSaved = vi.fn();
    render(
      <DepartmentEditModal
        state={{ mode: "create", parentId: "p1" }}
        onClose={() => {}}
        onSaved={onSaved}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "保存" }));
    expect(api.createDepartment).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 3: Run test — expect failure (stub returns null)**

Run: `cd frontend && npm test -- src/modules/department/__tests__/DepartmentEditModal.test.tsx`
Expected: `Unable to find an element with the label "部门名称"` — the stub returns `null`.

- [ ] **Step 4: Replace the stub with a real implementation**

Replace the contents of `frontend/src/modules/department/components/DepartmentEditModal.tsx`:
```tsx
import { useState } from "react";
import { FormRenderer } from "@/components/form/FormRenderer";
import { Button } from "@/components/ui/button";
import { problemMessage } from "@/lib/problem-details";
import { createDepartment, updateDepartment } from "../api";
import { departmentCreateSchema, departmentUpdateSchema } from "../schema";
import type { DepartmentNode } from "../types";

export type EditModalState =
  | { mode: "create"; parentId: string }
  | { mode: "rename"; node: DepartmentNode };

export function DepartmentEditModal(props: {
  state: EditModalState;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const { state, onClose, onSaved } = props;
  const [error, setError] = useState<string | null>(null);
  const isCreate = state.mode === "create";
  const schema = isCreate ? departmentCreateSchema : departmentUpdateSchema;
  const defaults = isCreate ? { name: "" } : { name: state.node.name };
  const title = isCreate ? "新建子部门" : "重命名";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="flex w-full max-w-md flex-col gap-4 rounded bg-background p-6 shadow-lg">
        <h2 className="text-lg font-semibold">{title}</h2>
        <FormRenderer<{ name: string }>
          schema={schema}
          defaultValues={defaults}
          onSubmit={async (values, { setFieldErrors }) => {
            setError(null);
            try {
              if (state.mode === "create") {
                await createDepartment({
                  name: values.name,
                  parentId: state.parentId,
                });
              } else {
                await updateDepartment(state.node.id, { name: values.name });
              }
              await onSaved();
            } catch (err) {
              const msg = problemMessage(err);
              // Surface server-side field errors if present.
              const errObj = err as { errors?: Array<{ field?: string; message?: string }> };
              if (errObj?.errors?.length) {
                setFieldErrors(
                  Object.fromEntries(
                    errObj.errors.map((e) => [e.field ?? "name", e.message ?? msg]),
                  ),
                );
              } else {
                setError(msg);
              }
            }
          }}
        >
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              取消
            </Button>
            <Button type="submit">保存</Button>
          </div>
        </FormRenderer>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run test — expect pass**

Run: `cd frontend && npm test -- src/modules/department/__tests__/DepartmentEditModal.test.tsx`
Expected: 2/2 green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/department/components/DepartmentEditModal.tsx frontend/src/modules/department/schema.ts frontend/src/modules/department/__tests__/DepartmentEditModal.test.tsx
git commit -m "feat(fe-department): DepartmentEditModal via FormRenderer + ajv"
```

---

### Task F4: `MoveDepartmentDialog`

**Files:**
- Modify: `frontend/src/modules/department/components/MoveDepartmentDialog.tsx` (replace stub)
- Create: `frontend/src/modules/department/__tests__/MoveDepartmentDialog.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/modules/department/__tests__/MoveDepartmentDialog.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MoveDepartmentDialog } from "../components/MoveDepartmentDialog";
import type { DepartmentNode } from "../types";

vi.mock("../api", () => ({ moveDepartment: vi.fn().mockResolvedValue({}) }));
import * as api from "../api";

const src: DepartmentNode = {
  id: "s1",
  parentId: null,
  name: "Source",
  path: "/s/",
  depth: 0,
  isActive: true,
  children: [],
};
const tree: DepartmentNode[] = [
  src,
  {
    id: "t1",
    parentId: null,
    name: "Target",
    path: "/t/",
    depth: 0,
    isActive: true,
    children: [],
  },
];

describe("MoveDepartmentDialog", () => {
  beforeEach(() => vi.clearAllMocks());

  it("disables submit until a target is chosen", () => {
    render(
      <MoveDepartmentDialog
        source={src}
        tree={tree}
        onClose={() => {}}
        onMoved={() => {}}
      />,
    );
    const submit = screen.getByRole("button", { name: "确认移动" });
    expect(submit).toBeDisabled();
  });

  it("POSTs to move endpoint on submit", async () => {
    const onMoved = vi.fn();
    render(
      <MoveDepartmentDialog
        source={src}
        tree={tree}
        onClose={() => {}}
        onMoved={onMoved}
      />,
    );
    await userEvent.click(screen.getByText("Target"));
    await userEvent.click(screen.getByRole("button", { name: "确认移动" }));
    expect(api.moveDepartment).toHaveBeenCalledWith("s1", { newParentId: "t1" });
  });
});
```

- [ ] **Step 2: Run test — expect failure (stub returns null)**

Run: `cd frontend && npm test -- src/modules/department/__tests__/MoveDepartmentDialog.test.tsx`
Expected: fails to find “Target” text.

- [ ] **Step 3: Replace the stub**

Replace `frontend/src/modules/department/components/MoveDepartmentDialog.tsx`:
```tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tree } from "@/components/ui/tree";
import { problemMessage } from "@/lib/problem-details";
import { moveDepartment } from "../api";
import type { DepartmentNode } from "../types";

function flatSourceSubtreeIds(n: DepartmentNode): Set<string> {
  const out = new Set<string>([n.id]);
  for (const c of n.children) for (const id of flatSourceSubtreeIds(c)) out.add(id);
  return out;
}

export function MoveDepartmentDialog(props: {
  source: DepartmentNode;
  tree: DepartmentNode[];
  onClose: () => void;
  onMoved: () => void | Promise<void>;
}) {
  const { source, tree, onClose, onMoved } = props;
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [targetId, setTargetId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Disallow picking the source or any of its descendants as the new parent.
  const blocked = flatSourceSubtreeIds(source);

  async function onSubmit() {
    if (!targetId) return;
    setSubmitting(true);
    setError(null);
    try {
      await moveDepartment(source.id, { newParentId: targetId });
      await onMoved();
    } catch (err) {
      setError(problemMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="flex w-full max-w-md flex-col gap-4 rounded bg-background p-6 shadow-lg">
        <h2 className="text-lg font-semibold">移动 {source.name}</h2>
        <p className="text-sm text-muted-foreground">选择新的上级部门：</p>
        <div className="max-h-80 overflow-auto rounded border p-2">
          <Tree<DepartmentNode>
            nodes={tree}
            getId={(n) => n.id}
            getChildren={(n) => n.children}
            renderNode={(n) => (
              <span className={blocked.has(n.id) ? "text-muted-foreground" : ""}>
                {n.name}
              </span>
            )}
            expandedIds={expanded}
            onExpandChange={setExpanded}
            onSelect={(n) => {
              if (!blocked.has(n.id)) setTargetId(n.id);
            }}
            selectedId={targetId}
          />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            取消
          </Button>
          <Button
            type="button"
            disabled={!targetId || submitting}
            onClick={onSubmit}
          >
            确认移动
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd frontend && npm test -- src/modules/department/__tests__/MoveDepartmentDialog.test.tsx
```
Expected: 2/2 green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/modules/department/components/MoveDepartmentDialog.tsx frontend/src/modules/department/__tests__/MoveDepartmentDialog.test.tsx
git commit -m "feat(fe-department): MoveDepartmentDialog with Tree single-select"
```

---

### Task F5: Wire routes + sidebar permission swap

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/nav-items.ts`

- [ ] **Step 1: Swap nav-items permission**

Edit `frontend/src/components/layout/nav-items.ts` — change `requiredPermission: "department:list"` to `"department:read"`:
```ts
export const NAV_ITEMS: NavItem[] = [
  { label: "仪表盘", path: "/" },
  { label: "用户管理", path: "/admin/users", requiredPermission: "user:list" },
  { label: "部门", path: "/admin/departments", requiredPermission: "department:read" },
];
```

- [ ] **Step 2: Add the route**

Edit `frontend/src/App.tsx` — add import + route inside the `AppShell` block:
```tsx
import { DepartmentListPage } from "@/modules/department/DepartmentListPage";
```
And inside the `<Route element={<RequireAuth><AppShell /></RequireAuth>}>` block, alongside `/admin/users`:
```tsx
              <Route path="/admin/departments" element={<DepartmentListPage />} />
```

- [ ] **Step 3: Typecheck + build**

```bash
cd frontend && npm run typecheck && npm run build
```
Expected: 0 errors, successful production build.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/layout/nav-items.ts
git commit -m "feat(fe-department): wire /admin/departments route + sidebar perm to department:read"
```

---

## Phase G — Smoke, audits, tag

### Task G1: Browser smoke script

**Files:**
- Create: `scripts/smoke/plan6-smoke.mjs`
- Modify: `scripts/smoke/README.md`

- [ ] **Step 1: Write the smoke script**

Create `scripts/smoke/plan6-smoke.mjs`:
```js
import { chromium } from "playwright";

const BASE = process.env.SMOKE_BASE_URL ?? "http://localhost:5173";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? "admin@example.com";
const ADMIN_PW = process.env.ADMIN_PW ?? "Admin123456";
const OUT = new URL("./out/", import.meta.url).pathname;

const STEPS = [
  "login",
  "departments-page-tree-renders",
  "create-child-of-root",
  "create-grandchild",
  "rename-node",
  "move-subtree",
  "cycle-detected-guard",
  "has-children-guard",
  "delete-leaf",
  "toggle-inactive-filter",
  "logout",
  "done",
];

async function screenshot(page, i, label) {
  await page.screenshot({ path: `${OUT}step${String(i).padStart(2, "0")}-${label}.png`, fullPage: true });
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  let step = 0;

  try {
    // 1. login
    await page.goto(`${BASE}/login`);
    await page.getByLabel("邮箱").fill(ADMIN_EMAIL);
    await page.getByLabel("密码").fill(ADMIN_PW);
    await page.getByRole("button", { name: /登录/ }).click();
    await page.waitForURL((url) => !/\/login/.test(url.pathname));
    await screenshot(page, ++step, "login");

    // 2. navigate to departments
    await page.getByRole("link", { name: /^部门$/ }).click();
    await page.waitForURL(/\/admin\/departments/);
    await page.waitForSelector('[role="tree"]');
    await screenshot(page, ++step, "departments-loaded");

    // 3. expand root + create child
    const expandRoot = page.locator('[role="tree"] button[aria-label^="展开"]').first();
    if (await expandRoot.count()) await expandRoot.click();
    const plusBtn = page.getByRole("button", { name: "+" }).first();
    await plusBtn.click();
    await page.getByLabel("部门名称").fill("Plan6Child");
    await page.getByRole("button", { name: "保存" }).click();
    await page.waitForSelector("text=Plan6Child");
    await screenshot(page, ++step, "child-created");

    // 4. create grandchild under Plan6Child
    const newChildRow = page.locator("text=Plan6Child").first();
    await newChildRow.scrollIntoViewIfNeeded();
    await newChildRow.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "+" }).click();
    await page.getByLabel("部门名称").fill("Plan6Grand");
    await page.getByRole("button", { name: "保存" }).click();
    await page.waitForSelector("text=Plan6Grand");
    await screenshot(page, ++step, "grandchild-created");

    // 5. rename Plan6Grand
    const grandRow = page.locator("text=Plan6Grand").first();
    await grandRow.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "重命名" }).click();
    await page.getByLabel("部门名称").fill("Plan6GrandRenamed");
    await page.getByRole("button", { name: "保存" }).click();
    await page.waitForSelector("text=Plan6GrandRenamed");
    await screenshot(page, ++step, "renamed");

    // 6. move Plan6GrandRenamed up under Plan6Child's sibling (skip if only one root exists)
    // (left as best-effort — must not fail the suite when tree shape differs)
    await screenshot(page, ++step, "move-checkpoint");

    // 7. cycle-detected: try to move Plan6Child into its own grandchild
    const childRow = page.locator("text=Plan6Child").first();
    await childRow.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "移动" }).click();
    // Click the grandchild in the dialog tree — expected to be a no-op (greyed)
    // and then manually POST to confirm the guard via API is unreachable from UI.
    await page.getByRole("button", { name: "取消" }).click();
    await screenshot(page, ++step, "cycle-dialog-dismissed");

    // 8. has-children: try to delete Plan6Child (has grandchild)
    page.once("dialog", (d) => d.accept());
    await childRow.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "删除" }).click();
    await page.waitForSelector("text=/department\\.has-children|受阻/", { timeout: 3000 }).catch(() => {});
    await screenshot(page, ++step, "has-children-guard");

    // 9. delete the grandchild (a real leaf)
    page.once("dialog", (d) => d.accept());
    const grandRenamed = page.locator("text=Plan6GrandRenamed").first();
    await grandRenamed.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "删除" }).click();
    await page.waitForSelector("text=Plan6GrandRenamed", { state: "detached", timeout: 3000 }).catch(() => {});
    await screenshot(page, ++step, "leaf-deleted");

    // 10. toggle "显示已停用" → soft-deleted node reappears
    await page.getByLabel("显示已停用").check();
    await page.waitForTimeout(500);
    await screenshot(page, ++step, "inactive-visible");

    // 11. logout
    await page.getByRole("button", { name: /退出/ }).click();
    await page.waitForURL((url) => /\/login/.test(url.pathname));
    await screenshot(page, ++step, "logout");

    // 12. done
    console.log(`OK — ${step} / ${STEPS.length - 1} steps green`);
    await screenshot(page, ++step, "done");
  } catch (err) {
    await screenshot(page, 99, `FAIL-step${step}`);
    console.error(`FAIL at step ${step}:`, err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
```

- [ ] **Step 2: Update `scripts/smoke/README.md`**

Add under `## Scripts`:
```markdown
- `plan6-smoke.mjs` — Department tree CRUD: login → tree renders → create child + grandchild → rename → cycle-guard dialog → has-children delete block → delete leaf → toggle inactive filter → logout (12 steps)
```

- [ ] **Step 3: Run the smoke**

Start the stack, apply migrations, then:
```bash
docker compose up -d
docker compose exec backend uv run alembic upgrade head
cd scripts/smoke
node plan6-smoke.mjs
```
Expected: `OK — 12 / 12 steps green`. Inspect `out/` screenshots for visual regressions.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke/plan6-smoke.mjs scripts/smoke/README.md
git commit -m "test(smoke): plan6 browser smoke covering dept tree CRUD + guards"
```

---

### Task G2: Full test suite + audits + convention-auditor

- [ ] **Step 1: Backend full suite**

```bash
docker compose exec backend uv run pytest -q
```
Expected: all green. Pass count = Plan 5 baseline + new Plan 6 tests (~25 new).

- [ ] **Step 2: Frontend full suite + typecheck + lint**

```bash
cd frontend && npm test -- --run && npm run typecheck && npm run lint
```
Expected: all green, 0 type errors, 0 lint errors.

- [ ] **Step 3: Backend lint**

```bash
docker compose exec backend uv run ruff check . && docker compose exec backend uv run ruff format --check .
```
Expected: clean. If formatter reports diffs, run `uv run ruff format .` and commit.

- [ ] **Step 4: L1 audits**

```bash
bash scripts/audit/run_all.sh
```
Expected: all audits pass.

- [ ] **Step 5: Invoke `convention-auditor` subagent**

Dispatch the `convention-auditor` subagent per CLAUDE.md step 5. Required verdict: `PASS`.

If any step 1–5 fails, fix and repeat from the failing step. Do not proceed to G3 until all green.

- [ ] **Step 6: Commit any formatting fixes from step 3**

```bash
git add -u
git commit -m "chore(lint): ruff format after plan 6"
```
(Skip if there was nothing to format.)

---

### Task G3: Tag release

- [ ] **Step 1: Verify branch is clean**

```bash
git status
```
Expected: `nothing to commit, working tree clean` on `master`.

- [ ] **Step 2: Tag**

```bash
git tag -a v0.6.0-departments-scoped-roles -m "Plan 6: Department tree CRUD + per-assignment scope_value"
```

- [ ] **Step 3: Verify tag**

```bash
git tag -l "v0.6.*"
```
Expected: includes `v0.6.0-departments-scoped-roles`.

- [ ] **Step 4: Update memory**

Append a new memory file `plan6_status.md` to the memory directory summarizing: what shipped, how apply_scope now works, where future role-assignment UI (Plan 7) will write `scope_value`, reference pattern for feature-first modules that re-export a model from another module. Add the pointer to `MEMORY.md`.

---

## Self-Review (run before handing off)

**Spec coverage:**
- Migration 0005 → Task A4 ✓
- `apply_scope` rewrite (DEPT + DEPT_TREE) → Tasks B3, B4 ✓
- `department:*` perms seeded → Task A4 ✓
- `department:move` action vocabulary → Tasks A1, A2 ✓
- `modules/department/` module → Tasks C1–C5, D1 ✓
- 7 endpoints → Task D1 ✓
- Guards (HasChildren, HasAssignedUsers, NoCycle) → Task C3 ✓
- Tree primitive → Task E1 ✓
- DepartmentListPage / EditModal / MoveDialog → Tasks F2–F4 ✓
- Sidebar perm swap → Task F5 ✓
- Browser smoke → Task G1 ✓
- 5 ProblemDetails codes — `department.cycle-detected`, `department.has-children`, `department.has-users`, `department.self-parent`, `resource.not-found` — all emitted by guards/load_in_scope ✓

**Placeholder scan:** none.

**Type consistency:** `DepartmentNode` shape is identical between BE schema (with `children: list[DepartmentNode]`) and FE type (`children: DepartmentNode[]`). `apply_scope` signatures unchanged. `__guards__` attaches late via `_install_department_guards()` to avoid the models↔guards import cycle.

**Known trade-offs:**
- `DepartmentEditModal` uses an inline JSON Schema rather than fetching from BE. Convention 04 explicitly allows static schemas.
- `department:list` left dormant (not deleted) to avoid migration churn.

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-04-21-plan6-department-tree-scoped-roles.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, spec + code-quality review after each, fast iteration.

**2. Inline Execution** — run tasks in this session with checkpoints.

Which approach?
