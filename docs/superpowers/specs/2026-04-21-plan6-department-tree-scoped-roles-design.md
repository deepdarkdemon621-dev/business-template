# Plan 6 — Department Tree CRUD + Per-Assignment Role Scope

**Date:** 2026-04-21
**Target release:** `v0.6.0-departments-scoped-roles`
**Predecessor:** `v0.5.0-admin-user-crud`

## Goal

1. Admins can CRUD the department tree from the UI (create, rename, move, soft-delete).
2. `UserRole` gains a nullable `scope_value` column anchoring each assignment to a specific department. `apply_scope` reads it. `null` preserves current behaviour (fall back to the user's own `department_id`), so Plan 4/5 call sites stay green without edits.
3. A single Alembic migration (0005) ships the schema change. No data migration needed — existing rows keep `scope_value = NULL` and behave identically to today.

## Non-Goals (Plan 7)

- Role CRUD + RolePermission editor UI.
- Role-assignment UI with per-assignment department picker. (Plan 6 adds the *data model* for per-assignment scope; Plan 7 adds the UI that exploits it. Until Plan 7 ships, `scope_value` stays null in practice and behaviour is unchanged.)
- `UserEditPage` migration to `<FormRenderer>` (already in `docs/backlog.md`).
- `LastOfKind` READ COMMITTED race fix (already in backlog).

## Architecture Overview

Two logically independent changes rolled into one plan because they share a migration window:

1. **Department module** — new feature-first module `modules/department/` that owns CRUD + move on the `Department` model (which continues to live in `rbac/models.py`, imported by the new module). Mirrors how `modules/user` imports `User` from `modules/auth/models`.
2. **Per-assignment scope** — `user_roles.scope_value` column + `apply_scope` rewrite in `app/core/permissions.py`. No FE change in Plan 6; the column is written only via CLI/seed until Plan 7's UI.

## Data Model

### Migration 0005

```sql
ALTER TABLE user_roles
  ADD COLUMN scope_value UUID NULL
  REFERENCES departments(id) ON DELETE SET NULL;

CREATE INDEX ix_user_roles_scope_value
  ON user_roles(scope_value)
  WHERE scope_value IS NOT NULL;
```

**Semantics:**
- `scope_value IS NULL` → anchor scope to the user's own `users.department_id` (existing Plan 4 behaviour).
- `scope_value = X` → anchor this assignment's dept/dept_tree scope to department X. Superadmin and `global`-scoped permissions ignore `scope_value`.
- `ON DELETE SET NULL` — if a department is hard-deleted, dependent assignments fall back to the user's own department rather than erroring.

### No changes to Role / RolePermission / Permission

Per-assignment scope lives on `UserRole`, not on `RolePermission`. `RolePermission.scope` still declares the *kind* of scope (global/dept_tree/dept/own); `UserRole.scope_value` provides the *value* for dept/dept_tree scopes when the anchor shouldn't be the user's own dept.

## Backend Components

### `modules/department/` (new)

Standard feature-first layout per convention 08:

- `models.py` — re-exports `Department` from `rbac.models` (no new model).
- `schemas.py` — `DepartmentCreateIn`, `DepartmentUpdateIn`, `DepartmentMoveIn`, `DepartmentOut`, `DepartmentNode` (tree node with `children`). All inherit `BaseSchema`.
- `crud.py` — `get`, `list_flat`, `get_tree_rooted_at`, `create`, `update`, `soft_delete`, `move`.
- `service.py` — `DepartmentService` with `move_department(id, new_parent_id)` implementing materialized-path subtree rewrite + depth sync + cycle detection.
- `router.py` — endpoints below.
- `CLAUDE.md` — module guide.

### Endpoints

| Method | Path                           | Perm               | Response         | Notes                                      |
|--------|--------------------------------|--------------------|------------------|--------------------------------------------|
| GET    | `/departments`                 | `department:read`  | `Page<Out>`      | Flat paginated list (convention 05 compliant) |
| GET    | `/departments/tree`            | `department:read`  | `DepartmentNode[]` | Full tree, scoped via `apply_scope`. Bounded cardinality — no pagination. |
| GET    | `/departments/{id}`            | `department:read`  | `DepartmentOut`  | `load_in_scope`                            |
| POST   | `/departments`                 | `department:create`| `DepartmentOut`  | `parentId` required (new roots only via seed/CLI) |
| PATCH  | `/departments/{id}`            | `department:update`| `DepartmentOut`  | `name` only (move has its own endpoint)    |
| POST   | `/departments/{id}/move`       | `department:move`  | `DepartmentOut`  | Body: `{newParentId}`                      |
| DELETE | `/departments/{id}`            | `department:delete`| 204              | Soft-delete (`is_active=false`); guards reject non-empty |

**Convention 05 note:** the `/departments/tree` endpoint is an explicit exception to the "lists paginate" rule. Justification: tree rendering needs the full subtree for UX; departments are bounded (typically <1000 per tenant). Flat list still paginates.

### `apply_scope` rewrite

Current (Plan 4):
```python
if scope == ScopeEnum.DEPT:
    return stmt.where(field == user.department_id)
```

New (Plan 6):
```python
if scope == ScopeEnum.DEPT:
    # Union of per-assignment scope_values for roles granting this perm,
    # falling back to user.department_id when scope_value IS NULL.
    dept_ids = select(
        func.coalesce(UserRole.scope_value, user.department_id)
    ).join(RolePermission, ...).join(Permission, Permission.code == code) \
     .where(UserRole.user_id == user.id)
    return stmt.where(field.in_(dept_ids))
```

DEPT_TREE follows the same pattern, expanding each anchor dept to its subtree via `Department.path LIKE`.

**Backward compatibility:** with `scope_value = NULL` on all rows (the state immediately after migration 0005), the subquery degenerates to `user.department_id` for every role — identical to Plan 4. The existing Plan 4 unit tests for `apply_scope` stay green unchanged and act as the backward-compat lock.

### Guards

Add to `Department.__guards__` in `rbac/models.py`:
- `HasChildren` — reject `soft_delete` if any active child rows.
- `HasAssignedUsers` — reject `soft_delete` if any `users.department_id == this.id` where `is_active=true`.
- `NoCycle` — reject `move` if `new_parent_id` is in the subtree of `id`. Also rejects `new_parent_id == id` (self-parent).

### Permission seeds

Migration 0005 also seeds into `permissions`:
- `department:create`, `department:read`, `department:update`, `department:delete`, `department:move`

Grants to built-in `admin` role: all five at `global` scope.

## Frontend Components

### `modules/department/`

Mirrors backend. `api.ts`, `types.ts`, `DepartmentListPage.tsx`, `DepartmentEditPage.tsx`, `components/MoveDepartmentDialog.tsx`, `__tests__/`.

### `@/components/ui/tree.tsx` (new primitive)

Thin recursive tree component. Props: `nodes`, `renderNode`, `expandedIds`, `onExpandChange`, `onSelect`. Hand-rolled (≤80 LOC) — no new dep. Styled with existing design tokens. Used by `DepartmentListPage` (as the main view) and reused inside `MoveDepartmentDialog` (as the parent picker).

### Pages

- `DepartmentListPage` — renders `<Tree>` of the `/departments/tree` response. Each node has inline buttons: Rename, Move, Soft-delete, + Child. "+ Child" and "Rename" open `DepartmentEditPage` in a modal (for consistency with `MoveDepartmentDialog` — no routing thrash on frequent edits). Shows soft-deleted nodes greyed out behind a toggle `?is_active=false`.
- `DepartmentEditPage` — create/rename using `<FormRenderer>` (convention 04 compliant — opens the door for UserEditPage to follow in Plan 7). Schema derived from `DepartmentCreateIn`/`UpdateIn`.
- `MoveDepartmentDialog` — embeds `<Tree>` with single-select; submit calls `POST /departments/{id}/move`.

### Sidebar

Existing "部门" link already routes to `/admin/departments`. No sidebar change; the page just stops being empty.

## Error Semantics (ProblemDetails codes)

| Code                          | Status | Trigger                                           |
|-------------------------------|--------|---------------------------------------------------|
| `department.cycle-detected`   | 409    | Move would place node under its own descendant    |
| `department.has-children`     | 409    | Delete with active children                       |
| `department.has-users`        | 409    | Delete while users are still assigned to the dept |
| `department.self-parent`      | 409    | `newParentId == id` on move                       |
| `resource.not-found`          | 404    | Standard scope-guarded 404 (existing)             |

FE surfaces these via existing `problemMessage()` — no new FE error infrastructure.

## Testing Strategy

### Backend
- **Migration 0005**: upgrade creates column + index + seeds; downgrade is clean (drop column, remove seeded perms).
- **`apply_scope` compat**: re-run every Plan 4 `apply_scope` unit test unchanged. All must pass (lock: scope_value=NULL state is semantically identical to Plan 4).
- **`apply_scope` new behaviour**: with `scope_value=X`, a user can see rows in dept X even if their `users.department_id` is different.
- **`move_department`**: path/depth correctness on a 4-level tree; cycle detection; move to same parent is no-op; descendants' scope_value references still resolve correctly post-move.
- **Guards**: `HasChildren`, `HasAssignedUsers`, `NoCycle` each have a red-green test.

### Frontend
- `Tree` primitive unit test: renders nested, expand/collapse, onSelect.
- `DepartmentListPage` test with mocked `/departments/tree`: tree renders, delete guard shows error toast.
- `DepartmentEditPage` test: uses `<FormRenderer>`, ajv blocks empty name, server-side field errors surface via `setFieldErrors`.
- `MoveDepartmentDialog` test: clicking a node enables submit, submit POSTs to `/move`.

### Browser smoke (`scripts/smoke/plan6-smoke.mjs`)
12-step Chrome-driven flow: admin login → departments page (tree renders) → create child of existing root → create grandchild → rename → move subtree to different parent → attempt move-into-own-descendant (expect `department.cycle-detected`) → attempt delete node with children (expect `department.has-children`) → delete leaf → toggle `?is_active=false` to verify soft-deleted node reappears greyed → logout.

## Risks & Mitigations

1. **`apply_scope` rewrite is load-bearing code.** Any regression breaks every scoped endpoint. *Mitigation:* all Plan 4 `apply_scope` tests stay unchanged and run in CI; the rewrite is required to make them pass. A new test matrix adds scope_value≠NULL cases without mutating the backward-compat cases.
2. **`move_department` materialized-path rewrite.** Wrong LIKE prefix or missing transaction → corrupt tree. *Mitigation:* single function, dedicated tests across 3 shapes (move leaf, move subtree, move-into-own-descendant rejection). All mutations wrapped in `async with session.begin()`.
3. **Tree primitive built from scratch.** *Mitigation:* keep it minimal — no drag-and-drop, no virtual scroll, no keyboard nav beyond Tab/Enter. If we need those later, they can be added to the primitive without breaking consumers.
4. **`scope_value` orphaning.** If a dept is hard-deleted, dependent `user_roles` rows lose their anchor. *Mitigation:* `ON DELETE SET NULL` — assignment falls back to user's own dept rather than erroring. Soft-delete (the default path) keeps the dept row and the FK intact.

## Out of Scope / Deferred

- Role CRUD + RolePermission editor UI — Plan 7.
- Role-assignment UI with dept picker per assignment (the UI that actually *writes* non-null `scope_value`) — Plan 7.
- `UserEditPage` migration to `<FormRenderer>` — Plan 7 or standalone (already backlogged 2026-04-21).
- Department tree drag-and-drop move — V2 (modal-based move ships in Plan 6).
- `LastOfKind` READ COMMITTED race — backlog 2026-04-20.
- `users.last_login_at` — backlog 2026-04-20.
- i18n (EN→JA) — backlog 2026-04-17.
