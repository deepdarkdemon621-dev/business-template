# Plan 5 — Admin User CRUD (minimal prototype)

**Date:** 2026-04-20
**Status:** Design — pending user review
**Target tag on completion:** `v0.5.0-admin-user-crud`
**Predecessor:** Plan 4 (RBAC), tag `v0.4.0-rbac`

## 1. Overview & goals

Plan 5 ships the first runtime admin surface on top of the RBAC engine delivered in Plan 4. The system currently has models, permission enforcement, and CLI role-grants, but **no way for a human admin to create users or assign roles through the UI** — the whole application is unusable without this layer.

This plan does the minimum to close that gap: the two missing UI primitives (`DataTable`, `AppShell`), a new backend `modules/user/` that exposes admin CRUD over the existing `User` model, and the first-touch frontend pages to drive it.

### V1 scope (this plan)
- **Frontend primitives** — previously-empty dirs:
  - `components/table/DataTable.tsx` — server-paginated/sorted/filtered table bound to `Page<T>` responses; empty/loading/error states.
  - `components/layout/{AppShell,Sidebar,TopBar}.tsx` — authenticated shell with permission-gated nav, user menu, `<Outlet />` workspace.
- **Backend `modules/user/`** — admin CRUD over the existing `User` model (which stays in `modules/auth/`):
  - `GET /users` — list, paginated, scope-aware.
  - `POST /users` — create user (admin supplies initial password; `must_change_password=true`).
  - `GET /users/{id}` — detail, includes assigned roles.
  - `PATCH /users/{id}` — update (full_name, department_id, is_active).
  - `DELETE /users/{id}` — soft delete (`is_active=false`).
  - `POST /users/{id}/roles/{role_id}` — assign role (idempotent upsert).
  - `DELETE /users/{id}/roles/{role_id}` — revoke role (idempotent; 404 if not assigned).
- **Self-protection guards** — two new entries in `ServiceGuardRegistry`:
  - `SelfProtection()` — forbids delete/deactivate/role-strip of `current_user.id == target.id`.
  - `LastOfKind(role_code="superadmin")` — forbids removing the superadmin role from the system's last superadmin.
  - Both are bypassed when `current_user.is_superadmin == True`, consistent with spec §5.7.
- **Frontend `modules/user/`**:
  - `UserListPage.tsx` — DataTable with columns: email / full_name / department / status / actions.
  - `UserEditPage.tsx` — create and edit modes, FormRenderer driven, includes a `RoleAssignmentPanel` subcomponent on edit.
- **AppShell integration** — routes `/admin/users`, `/admin/users/new`, `/admin/users/:id`; sidebar nav entry shown when `user:list` is granted.

### Non-goals (deferred — see `docs/backlog.md`)
- Department tree CRUD UI (create/rename/move/delete nodes).
- Role CRUD + RolePermission matrix editor.
- Audit-log viewer UI.
- Admin-scoped session management (revoke remote sessions).
- `last_login_at` field on User.
- Email delivery of admin-created credentials (we chose manual admin-set password for V1).

## 2. Architecture

### 2.1 Backend module layout

`backend/app/modules/user/` is a new feature module. It does **not** own a model — the `User` SQLAlchemy model stays in `modules/auth/models.py` to avoid a sprawling refactor. The new module re-uses it via import.

```
backend/app/modules/user/
├── CLAUDE.md
├── __init__.py
├── schemas.py       # UserCreateIn, UserUpdateIn, UserOut, UserDetailOut, RoleAssignIn
├── service.py       # create_user / update_user / soft_delete_user / assign_role / revoke_role
├── crud.py          # list_users / get_user_with_roles
└── router.py        # 7 endpoints registered into api/v1.py
```

Why service-layer self-protection uses the guard registry (D1=a): convention 02 reserves the registry for cross-entity business invariants, and "cannot remove the last superadmin" / "cannot deactivate self" are exactly that. Putting them in the registry sets the precedent for future bespoke rules (Role CRUD, Department tree) rather than scattering `if … raise` across services.

### 2.2 Frontend module layout

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx        # <div><Sidebar/><main><TopBar/><Outlet/></main></div>
│   │   ├── Sidebar.tsx         # nav items filtered via usePermissions().can()
│   │   └── TopBar.tsx          # user menu (change password / sessions / logout)
│   └── table/
│       └── DataTable.tsx       # generic <DataTable<T> columns endpoint queryKey />
└── modules/user/
    ├── UserListPage.tsx
    ├── UserEditPage.tsx
    ├── components/
    │   └── RoleAssignmentPanel.tsx
    └── __tests__/
```

Router wiring: `App.tsx` wraps authenticated routes in `<AppShell />` via a layout route. Existing pages (`/`, `/me/sessions`, `/password-change`) move inside the shell; unauthenticated pages (`/login`, `/password-reset*`, `/403`) stay outside.

### 2.3 Data flow

**List** — `UserListPage` → `DataTable` → `axios.get("/api/v1/users", {params: pq})` → `Page<UserOut>` → row render.

**Create** — `UserEditPage` (new mode) → `FormRenderer` schema from `UserCreateIn.model_json_schema()` → submit → `POST /users` → 201 → navigate to `/admin/users/:id`.

**Role assignment** — `RoleAssignmentPanel` diffs current vs. desired role set → emits a sequence of `POST` / `DELETE /users/{id}/roles/{role_id}`. Each mutation is independent and idempotent; the UI disables controls while in-flight and refetches the user detail on completion.

## 3. Data model

No new tables. No migration. Plan 5 only consumes what Plan 4 already shipped:

- `users` — existing columns unchanged.
- `user_roles` — the association table written through the new assign/revoke endpoints.
- `roles`, `departments` — read-only joins for detail responses.

## 4. Permissions

All permission codes already exist in the Plan 4 seed; Plan 5 introduces **no new permission rows**:

| Endpoint | Permission | Scope-aware |
|---|---|---|
| `GET /users` | `user:list` | yes — `apply_scope(User, …, "department_id")` |
| `POST /users` | `user:create` | no (global) |
| `GET /users/{id}` | `user:read` | yes — `load_in_scope` |
| `PATCH /users/{id}` | `user:update` | yes |
| `DELETE /users/{id}` | `user:delete` | yes |
| `POST /users/{id}/roles/{role_id}` | `user:assign` | yes on user, no on role |
| `DELETE /users/{id}/roles/{role_id}` | `user:assign` | yes on user, no on role |

The built-in `admin` role (Plan 4 seed) already holds `user:*`; no seed change needed.

## 5. Schemas & validation

Following convention 01 — Pydantic only, no hand-written JSON Schema. All schemas extend the shared `BaseSchema` from Plan 2 (`alias_generator=to_camel`, `populate_by_name=True`).

```python
class UserCreateIn(BaseSchema):
    __rules__ = [password_policy(field="password")]  # registered rule from Plan 3

    email: EmailStr
    password: str
    full_name: str = Field(min_length=1, max_length=100)
    department_id: UUID | None = None
    must_change_password: bool = True  # default true; admin can override

class UserUpdateIn(BaseSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    department_id: UUID | None = None
    is_active: bool | None = None

class UserOut(BaseSchema):
    id: UUID
    email: EmailStr
    full_name: str
    department_id: UUID | None
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime

class UserDetailOut(UserOut):
    roles: list[RoleSummaryOut]  # {id, code, name}
    department: DepartmentSummaryOut | None
```

`password_hash` is never in a response schema (convention anti-laziness #12). Password policy validation runs on both FE (ajv) and BE (Pydantic) via the already-registered rule from Plan 3.

## 6. Service guards

Two new guards added to `app/core/guards.py` registry:

```python
class SelfProtection(Guard):
    """Forbid target_id == current_user.id unless current_user.is_superadmin."""

class LastOfKind(Guard):
    """Forbid removing role `role_code` from the system's last holder, unless current_user.is_superadmin."""
    def __init__(self, role_code: str): ...
```

Attached on the `User` model via `__guards__`:

```python
class User(Base):
    __guards__ = {
        "delete": [SelfProtection()],
        "deactivate": [SelfProtection()],
        "strip_role": [SelfProtection(), LastOfKind("superadmin")],
    }
```

`DELETE /users/{id}` triggers the `delete` guard; `PATCH` with `is_active=false` triggers `deactivate`; `DELETE /users/{id}/roles/{role_id}` triggers `strip_role`. `LastOfKind("superadmin")` inspects the `ctx.role_code` passed by the service call and no-ops when it doesn't match, so the guard is cheap to always attach.

Failures raise `GuardViolationError(code, ctx)` → surfaces as Problem Details with a stable code (`self_protection`, `last_superadmin`).

## 7. Frontend specifics

### 7.1 DataTable

Generic on row type. Props:

```ts
type DataTableProps<T> = {
  columns: ColumnDef<T>[];
  endpoint: string;           // e.g. "/users"
  queryKey: readonly unknown[];
  initialSort?: SortState;
  filters?: Record<string, unknown>;
  rowActions?: (row: T) => ReactNode;
};
```

- Uses React Query for cache + refetch.
- Pagination state lives in URL search params (`?page=2&size=20&sort=-createdAt`).
- Never accepts a local array prop — compile-time enforcement of "no client pagination" (convention 99-anti-laziness #1).

### 7.2 AppShell

Layout route that wraps everything requiring auth:

```tsx
<Route element={<AppShell />}>
  <Route path="/" element={<DashboardPage />} />
  <Route path="/admin/users" element={<UserListPage />} />
  <Route path="/admin/users/new" element={<UserEditPage mode="create" />} />
  <Route path="/admin/users/:id" element={<UserEditPage mode="edit" />} />
  <Route path="/me/sessions" element={<SessionsPage />} />
  <Route path="/password-change" element={<PasswordChangePage />} />
</Route>
```

Sidebar entries are declarative `{label, path, requiredPermission}` records; hidden entirely when permission is missing (not greyed out — matches the "UX-only, BE re-checks" principle).

### 7.3 Form 5-layer consistency

Per `docs/conventions/10-form-consistency.md`, every field in `UserCreateIn` / `UserUpdateIn` must show the red-asterisk marker, on-blur validation, field-level error messages, BE validation, and DB constraint agreement. Explicitly verified during smoke test.

## 8. Testing

### 8.1 Backend
- Per-endpoint: 200 happy path, 403 when permission missing, 403 when out of scope, 404 when id unknown.
- Guards:
  - non-superadmin tries `DELETE /users/{self.id}` → 403 `self_protection`.
  - non-superadmin tries `PATCH /users/{self.id}` with `is_active=false` → 403.
  - non-superadmin tries `DELETE /users/{last_superadmin}/roles/{superadmin_role.id}` → 403 `last_superadmin`.
  - superadmin performs all three → 200 (bypass verified).
- Role assign idempotency: double-POST same (user, role) → 200 both times; DELETE unassigned role → 404 with stable code.
- Soft delete: `DELETE /users/{id}` → subsequent `GET /users/{id}` still returns (with `is_active=false`); user is excluded from default list, visible when `?is_active=false`.
- Scope correctness: dept-tree admin sees users in subtree only; `own` admin sees self only.

### 8.2 Frontend
- DataTable: click next-page → query params update → correct API call issued; empty state renders; error state renders.
- AppShell: missing `user:list` → sidebar entry absent; present → entry rendered + navigable.
- UserListPage / UserEditPage smoke via MSW mocks.
- 5-layer form consistency on `UserCreateIn` fields.

## 9. Verification gates

Before tagging `v0.5.0-admin-user-crud`:

1. `cd backend && uv run pytest` — all green.
2. `cd frontend && npm test && npm run typecheck && npm run lint` — all green.
3. `cd backend && uv run ruff check .` — clean.
4. `bash scripts/audit/run_all.sh` — all L1 audits pass (especially `audit_permissions`, `audit_scope`, `audit_listing`, `audit_pagination_fe`).
5. **Browser smoke test** (per `feedback_smoke_test_before_complete`):
   - Log in as superadmin → create user (manual password) → log out → log in as new user → forced to `/password-change` → change → land on dashboard.
   - As superadmin: assign/revoke roles on the new user → user re-login → `/me/permissions` reflects new grants (plus confirm nav/focus refetch works within the same session).
   - As non-superadmin admin: attempt self-deactivate → see `self_protection` error; attempt to remove superadmin role from the last superadmin → see `last_superadmin` error.
   - Soft-delete a user → vanishes from default list → reappears with `?is_active=false` filter toggle.
6. `convention-auditor` subagent invocation → `VERDICT: PASS`.
7. Only then tag and update memory (`plan5_status.md`).

## 10. Out-of-scope callouts

Anything not listed in §1 is deferred to `docs/backlog.md`. Particularly:
- No email delivery for new credentials — admin reads the password from their own form input.
- No bulk operations (import, mass-assign).
- No column customization / saved views in DataTable.
- No user avatar upload.
