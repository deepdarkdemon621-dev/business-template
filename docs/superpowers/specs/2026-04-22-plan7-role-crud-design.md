# Plan 7 — Role CRUD + RolePermission Editor (+ UserEditPage FormRenderer migration)

**Date:** 2026-04-22
**Target release:** `v0.7.0-role-crud`
**Predecessor:** `v0.6.0-departments-scoped-roles`

## Goal

1. Admins can CRUD roles from the UI: create, rename, change code, edit permission matrix, delete.
2. A permission-matrix editor renders all seeded permissions grouped by resource, with one 5-state scope choice per permission (`—` / `own` / `dept` / `dept_tree` / `global`). Whole-matrix save semantics: the PATCH body declares the desired end-state; the service diffs and commits atomically; one audit event per save.
3. Builtin roles (`admin`, `member`) are protected: matrix is editable (tenants can tune defaults), but `code` + `name` + existence are locked. `superadmin` is fully immutable.
4. Non-builtin role delete cascades via DB FK (`ON DELETE CASCADE` already set on `role_permissions.role_id` and `user_roles.role_id`), gated in the UI behind a typed-name confirmation dialog that surfaces the blast radius.
5. `UserEditPage` is migrated to `<FormRenderer>` (backlog item from 2026-04-21), retiring the last admin form that still hand-rolls `<Input>`/`<Label>` trees — eliminates a convention-04 violation and unifies all admin forms on one pattern.

## Non-Goals (later plans)

- Audit log viewer UI (Plan 8 candidate).
- Session management admin view (Plan 8+ candidate).
- `users.last_login_at` column (backlog).
- LoginPage/ResetPasswordPage/ChangePasswordPage required-field marker cleanup (backlog).
- `LastOfKind` READ COMMITTED race fix (backlog).
- Per-permission `allowed_scopes` constraint (any scope × any permission remains valid at data layer).
- Real-time permission push (SSE) for cross-session invalidation (backlog).
- i18n EN→JA cutover (all new strings go through the existing i18n surface; no hardcoded Japanese literals introduced).

## Architecture Overview

One logically coherent change bundled with one debt pay-down that shares its UI pattern:

1. **Role CRUD in `modules/rbac/`** — no new module. rbac already owns Role / Permission / RolePermission / UserRole. New `RoleService` + guards + router endpoints; reuses `PaginatedEndpoint`, `apply_scope`, `require_perm`, `ProblemDetails`.
2. **`<RolePermissionMatrix>` component** — standalone React component rendered alongside `<FormRenderer>` on the role editor page (same composition pattern as Plan 5 `UserEditPage` + `<RoleAssignmentPanel>`).
3. **`UserEditPage` → `<FormRenderer>`** — final admin-form migration, bundled because both forms (role editor, user editor) land on the same composition pattern simultaneously, preventing drift.

## Data Model

### Migration 0006 (data-only; no schema changes)

```sql
-- New permissions
INSERT INTO permissions (id, code, resource, action, description) VALUES
  (gen_random_uuid(), 'role:create', 'role', 'create', 'Create a role'),
  (gen_random_uuid(), 'role:update', 'role', 'update', 'Update role metadata or permissions'),
  (gen_random_uuid(), 'role:delete', 'role', 'delete', 'Delete a non-builtin role');

-- Seed grants: admin gets all three at scope=global; member gets none; superadmin unaffected (short-circuits).
INSERT INTO role_permissions (role_id, permission_id, scope)
SELECT r.id, p.id, 'global'
FROM   roles r, permissions p
WHERE  r.code = 'admin'
  AND  p.code IN ('role:create', 'role:update', 'role:delete');
```

**Downgrade:** `DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN (...))` then `DELETE FROM permissions WHERE code IN (...)`. Count-based test assertions per prior migration convention.

**No changes to** `roles`, `role_permissions`, `user_roles`, or `permissions` table definitions. Existing columns (`roles.is_builtin`, `roles.is_superadmin`, `role_permissions.scope`, and the existing `ON DELETE CASCADE` on both `role_permissions.role_id` and `user_roles.role_id`) cover all required semantics.

## Backend Components

### `modules/rbac/` additions

- `schemas.py` — new schemas (see below).
- `guards.py` — new guards: `BuiltinRoleLocked`, `SuperadminRoleLocked`, `UniqueRoleCode`, `PermissionCodeExists`.
- `service.py` — new `RoleService` with `create`, `update`, `delete`, `_replace_permissions` (internal helper for matrix diff logic).
- `crud.py` — CRUD helpers: `create_role`, `update_role_metadata`, `delete_role`, `list_role_permissions`, `replace_role_permissions`, `list_all_permissions`.
- `router.py` — new endpoints (table below). Existing `GET /roles` extended to return user/permission counts.

### Endpoints

| Method | Path               | Perm              | Response         | Notes |
|--------|--------------------|-------------------|------------------|-------|
| GET    | `/roles`           | `role:list`       | `Page<RoleListOut>`   | Extended: `userCount`, `permissionCount` aggregates. |
| GET    | `/roles/{id}`      | `role:read`       | `RoleDetailOut`       | Full permission matrix + user count. |
| POST   | `/roles`           | `role:create`     | `RoleDetailOut` (201) | Body: `RoleCreateIn`. Initial matrix optional. |
| PATCH  | `/roles/{id}`      | `role:update`     | `RoleDetailOut`       | Body: `RoleUpdateIn`. When `permissions` present, replaces whole set atomically. |
| DELETE | `/roles/{id}`      | `role:delete`     | `RoleDeletedOut` (200) | **Convention deviation:** existing DELETE endpoints return 204. Plan 7 returns 200 + body `{deletedUserRoles: N}` so the confirmation UI can surface the cascade count for audit/UX. Flagged for convention-auditor review. |
| GET    | `/permissions`     | `permission:list` | `Page<PermissionOut>` | Paginate per convention; default `size=100` (enough for all seeded perms — UI fetches once). |

### Schemas

```python
class RoleOut(BaseSchema):                   # existing; unchanged
    id: uuid.UUID
    code: str
    name: str
    is_builtin: bool
    is_superadmin: bool

class RoleListOut(RoleOut):                  # new
    user_count: int
    permission_count: int
    updated_at: datetime

class RolePermissionItem(BaseSchema):        # new
    permission_code: str
    scope: ScopeEnum

class RoleDetailOut(RoleOut):                # new
    permissions: list[RolePermissionItem]
    user_count: int
    updated_at: datetime

class RoleCreateIn(BaseSchema):              # new
    code: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(..., min_length=1, max_length=100)
    permissions: list[RolePermissionItem] = []

class RoleUpdateIn(BaseSchema):              # new
    code: str | None = Field(None, min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    name: str | None = Field(None, min_length=1, max_length=100)
    permissions: list[RolePermissionItem] | None = None  # None = metadata-only edit; [] = clear all grants

class RoleDeletedOut(BaseSchema):            # new
    id: uuid.UUID
    deleted_user_roles: int
```

### Guards (run in this order by service base before mutation)

| Guard                      | Fires on     | Check                                                                 |
|----------------------------|--------------|-----------------------------------------------------------------------|
| `SuperadminRoleLocked`     | update/delete| Refuses ALL mutations when `role.is_superadmin == True`.              |
| `BuiltinRoleLocked`        | update/delete| Refuses `code`/`name` edit and all delete when `role.is_builtin == True`. Matrix edits still allowed. |
| `UniqueRoleCode`           | create/update| `code` must not collide with any existing role. Relies on the existing `roles.code` unique index; service catches `IntegrityError` and re-raises as `role.code-conflict`. (No row-level lock needed — under READ COMMITTED the unique index is the source of truth.) |
| `PermissionCodeExists`     | create/update| Every `permission_code` in the payload must exist in `permissions`. |

### ProblemDetails error codes

Kebab-case with dot-namespace, matching existing conventions (`auth.invalid-token`, `department.has-children`):

- `role.not-found` → 404
- `role.builtin-locked` → 409 — attempted immutable-field edit on builtin
- `role.superadmin-locked` → 409 — attempted any mutation on superadmin
- `role.code-conflict` → 409 — duplicate `code`
- `role.permission-unknown` → 422 — payload references unseeded permission code

### `RoleService._replace_permissions` semantics

Called internally by `update` when `permissions` is present in the payload:

1. Load current `role_permissions` rows for the role.
2. Diff against desired set (keyed by `permission_code`): compute `added`, `removed`, `scope_changed`.
3. Inside `async with session.begin()`:
   - Delete `removed` rows.
   - Update scope on `scope_changed` rows.
   - Insert `added` rows.
4. Audit payload includes the three diff lists so the audit event is human-readable ("role X: added user:delete@dept, removed workflow:publish@global, changed department:read from dept to dept_tree").

Idempotent: empty diff → no writes, no audit event.

### Audit events

- `role.created` — payload: `{code, name, permissions: [...]}`
- `role.updated` — payload: `{metadata_changes: {code?, name?}, permissions: {added, removed, scope_changed}}`. Fields absent when unchanged.
- `role.deleted` — payload: `{code, name, deleted_user_roles: N}`. Captures cascade blast radius.

## Frontend Components

### Routes (new)

```
/admin/roles         → RoleListPage
/admin/roles/new     → RoleEditPage  (create mode)
/admin/roles/:id     → RoleEditPage  (edit mode)
```

### Sidebar entry

New "Roles" link in the admin section of `AppShell`'s sidebar, permission-gated on `role:read` (matches Plan 6's `department:read` wiring). Placed between "Users" and "Departments".

### `RoleListPage` — `frontend/src/pages/admin/RoleListPage.tsx`

`<DataTable server>` bound to `GET /roles`. Columns: **Code** (monospace) · **Name** · **Builtin** (badge: "Builtin" for `is_builtin && !is_superadmin`, "System" for superadmin, blank otherwise) · **# users** · **# perms** · **Updated** (relative time) · **Actions** (Edit / Delete).

**Delete UX:** Button is disabled (with tooltip "Builtin role cannot be deleted") when `is_builtin`. Otherwise opens `<DeleteRoleDialog>` — typed-name confirmation, body text `"This role is assigned to {userCount} users. Deleting will revoke the role from all of them. This cannot be undone."` Matches Plan 6 `DepartmentDeleteDialog` visual pattern.

### `RoleEditPage` — `frontend/src/pages/admin/RoleEditPage.tsx`

Two sections stacked vertically:

1. **Role metadata** — rendered by `<FormRenderer>` from a JSON Schema derived from `RoleCreateIn` / `RoleUpdateIn`. Fields: `code`, `name`. In edit mode, `code` is disabled when `is_builtin`; both fields + the whole form are read-only when `is_superadmin`. `ProblemDetails.errors` from 422 are surfaced via `setFieldErrors`.
2. **Permission matrix** — `<RolePermissionMatrix>`, rendered outside `<FormRenderer>`. Read-only when `is_superadmin`.

**Save button** collects renderer form state + matrix state → one `POST /roles` or `PATCH /roles/{id}` call. On success: invalidates `['roles']` query + `['permissions', 'me']` query (latter covers the "I just edited my own role" case — forces the current user's permissions cache to refresh without waiting for focus/nav). Navigates back to `/admin/roles`.

### `<RolePermissionMatrix>` — `frontend/src/components/rbac/RolePermissionMatrix.tsx`

Props: `value: RolePermissionItem[]`, `onChange: (next: RolePermissionItem[]) => void`, `allPermissions: PermissionOut[]`, `disabled?: boolean`.

Rendering:
- Fetches `/permissions` once (via React Query) and passes the result through `allPermissions` from the parent; lives in the parent page so it caches across re-mounts.
- Groups rows by `permission.resource`, each resource an `<details open>` collapsible section with a header showing "{resource} ({granted}/{total})".
- Each row: permission `code` (monospace) · description · `<RadioGroup>` with five options (`—` / `own` / `dept` / `dept_tree` / `global`). Selection is driven by `value.find(v => v.permission_code === perm.code)`; selecting `—` removes the entry from `value`; selecting any scope upserts it.
- `disabled` prop cascades to all radios (locks the entire matrix for superadmin).

Matrix-level bulk actions (future enhancement, not Plan 7): "grant all in this resource at X scope" / "clear all". Noted in backlog if UX demands it post-launch.

### `UserEditPage` → `<FormRenderer>` migration (bundled from backlog)

- Derive JSON Schema from `UserCreateIn` / `UserUpdateIn` (hand-authored next to the page, mirroring `DepartmentEditModal`).
- Replace hand-rolled `<Input>`/`<Label>` tree with `<FormRenderer schema={...} />`.
- Pipe `ProblemDetails.errors` from the API's 422 responses into `setFieldErrors`.
- Keep `<RoleAssignmentPanel>` *outside* the renderer, rendered below it in edit mode (unchanged behaviour).
- Register `passwordPolicy` custom rule in `@/lib/ajv.ts` if not already present (verify first — may have been registered for ResetPasswordPage/ChangePasswordPage already).
- Rewrite `UserEditPage.test.tsx` to query fields via the rendered labels (existing label strings should continue to match under the schema's `title` field).

### FE permission sync

No new mechanism. Per the saved FE/BE permission-sync feedback: `PermissionsProvider.refetch()` already fires on nav + focus. The `RoleEditPage` save handler adds an explicit `queryClient.invalidateQueries(['permissions', 'me'])` so self-edits propagate without waiting for navigation.

Cross-session invalidation (admin A edits role X while admin B holds it) remains staleness-tolerant until the SSE backlog item lands. Documented assumption; no change.

## Testing Strategy

### Backend pytest layers

- `tests/modules/rbac/test_role_crud.py` — CRUD helpers: create, update metadata, `_replace_permissions` diff correctness (empty/no-op/add-only/remove-only/scope-change/mixed), delete. Rejects unknown permission codes.
- `tests/modules/rbac/test_role_service.py` — service-level: guards fire in correct order; audit events emitted with correct payloads including matrix diff; cascade-delete removes `role_permissions` + `user_roles` rows.
- `tests/modules/rbac/test_role_guards.py` — `BuiltinRoleLocked` refuses `code`/`name` on `admin`/`member` but allows matrix edits; `SuperadminRoleLocked` refuses all mutations on `superadmin`; `UniqueRoleCode` refuses duplicates (including a two-concurrent-session test); `PermissionCodeExists` rejects unknown codes.
- `tests/modules/rbac/test_api_role_crud.py` — endpoint-level: happy paths for all six endpoints; 403 for member caller on writes; 409/422 error codes with correct `ProblemDetails.code`; cascade count surfaced in DELETE response.
- `tests/migrations/test_0006.py` — upgrade from 0005 seeds three permissions + three admin grants (count-based); downgrade cleanly reverses. Runs against isolated test DB per the test-isolation feedback memory.

### Frontend vitest

- `src/pages/admin/__tests__/RoleListPage.test.tsx` — DataTable wiring, sort/filter, delete button disabled for builtin, delete dialog shows cascade count.
- `src/pages/admin/__tests__/RoleEditPage.test.tsx` — create flow end-to-end, edit flow, matrix disabled when superadmin, code disabled when builtin, FormRenderer surfaces ProblemDetails errors on field.
- `src/components/rbac/__tests__/RolePermissionMatrix.test.tsx` — render from `allPermissions`, resource grouping, radio changes emit correct `onChange` payloads, `disabled` prop locks every radio.
- `src/pages/admin/__tests__/UserEditPage.test.tsx` — rewritten for FormRenderer interaction (this is the migration's own test coverage).

### Playwright smoke — `frontend/tests/smoke/plan7_role_crud.spec.ts`

Real-browser golden path:
1. Admin logs in → navigates to `/admin/roles` → creates role `"tester"` with `user:read@global` + `department:list@own`.
2. Admin opens `/admin/users/<member>` → assigns `tester` role → saves.
3. Admin logs out. Member (holder of the new role) logs in → calls `/me/permissions` → confirms the two perms are present with expected scopes.
4. Admin logs back in → deletes `tester` role (types name in confirmation dialog). Member's session (via focus event in another tab) loses those perms.
5. Non-admin hits `/admin/roles` directly → permission-denied redirect.

### Gates before tag (per CLAUDE.md)

1. `cd backend && uv run pytest && cd ../frontend && npm test` — all green
2. `npm run typecheck` — clean
3. `uv run ruff check . && npm run lint` — clean
4. `bash scripts/audit/run_all.sh` — L1 audits pass (whitelist new `/permissions` listing if it triggers a listing-audit false-positive, same as Plan 6 `/tree`)
5. `convention-auditor` subagent → `VERDICT: PASS`
6. Playwright smoke green
7. Only then: tag `v0.7.0-role-crud`, push

## Rollout & Sequencing

Plan 7 implementation tasks (each discrete so `convention-auditor` can scope review):

1. **BE foundation** — migration 0006, schemas, guards, CRUD helpers, `RoleService`, router endpoints. Backend tests green.
2. **FE API layer** — `frontend/src/api/roles.ts`, `frontend/src/api/permissions.ts`. Types + fetchers. Typecheck green.
3. **`<RolePermissionMatrix>` component** — standalone + unit tests.
4. **`RoleListPage`** — routes, sidebar entry, delete dialog + tests.
5. **`RoleEditPage`** — FormRenderer + matrix composition + tests.
6. **`UserEditPage` → `<FormRenderer>` migration** — bundled pay-down.
7. **Audits + convention-auditor gate.**
8. **Playwright smoke scenario** — must pass.
9. **Tag `v0.7.0-role-crud` + push.**

## Backlog items closed by Plan 7

- "Role CRUD + RolePermission editor" (`docs/backlog.md` 2026-04-20 scope-extensions entry).
- "Migrate `UserEditPage` → `<FormRenderer>`" (`docs/backlog.md` 2026-04-21 entry).

## Backlog items NOT closed (remain for future plans)

Audit-log viewer UI · Session admin view · LoginPage/ResetPasswordPage/ChangePasswordPage required-marker cleanup · `users.last_login_at` · `LastOfKind` race fix · per-permission `allowed_scopes` · real-time permission push (SSE) · i18n EN→JA.
