# Plan 4 — RBAC (Roles, Permissions, Departments)

**Date:** 2026-04-17
**Status:** Design — pending user review
**Target tag on completion:** `v0.4.0-rbac`
**Predecessor:** Plan 3 (auth), tag `v0.3.0-auth` + `fix(plan3-followup)` commit

## 1. Overview & goals

Plan 4 introduces the role-based access control substrate for the application: a permission/role/department data model, per-request enforcement utilities, seed data, a CLI for ops-level role management, frontend primitives for permission-aware UI, and two new L1 audits that keep future code from drifting. It also retroactively fixes the test-database isolation hole that Plan 3 exposed.

### V1 scope (this plan)
- Backend tables: `departments`, `permissions`, `roles`, `role_permissions`, `user_roles`; `users.department_id` FK.
- Core utilities: `require_perm`, `apply_scope`, `load_in_scope`, `get_user_permissions`.
- HTTP endpoints: `GET /me/permissions`, `GET /departments`.
- Typer CLI: `cli rbac grant-role|revoke-role|list-user|list-roles`.
- Alembic migration with seed data (permissions, three built-in roles, root department, superadmin promotion for `admin@example.com`).
- Frontend: `PermissionsProvider`, `usePermissions`, `<Gate>`, `<ProtectedByPermission>`, `/403` page, dev-only debug card on dashboard.
- L1 audits: `audit_scope.py`, `audit_schema_db_consistency.py`.
- Convention doc: `docs/conventions/10-form-consistency.md`.
- Test DB isolation: dedicated test DB, guard in `conftest.py`, transactional rollback fixture; existing Plan 3 tests migrated to the new fixture pattern.

### Non-goals (deferred — see `docs/backlog.md`)
- Admin UI for role/permission/department CRUD.
- Custom (non-builtin) roles or per-user scope overrides.
- Move-department-subtree operation.
- Real-time permission change propagation (SSE / WebSocket).
- Full i18n — Japanese UI translation.

## 2. Architecture

RBAC is a new first-class module: `backend/app/modules/rbac/`, sibling to `auth/`. It exposes:

- **Models** (`models.py`) — the five new tables.
- **Schemas** (`schemas.py`) — Pydantic payloads and responses.
- **CRUD** (`crud.py`) — DB access helpers.
- **Service** (`service.py`) — business logic including `get_user_permissions`, scope folding, and the three FastAPI dependencies `require_perm` / `apply_scope` / `load_in_scope`.
- **API** (`api.py`) — the two V1 HTTP endpoints.
- **Constants** (`constants.py`) — `ScopeEnum`, `ActionEnum`, `SUPERADMIN_ALL` sentinel.

The `auth/` module is modified in place to add `__scope_map__` to the `User` model and establish the FK relationship to `departments`.

Frontend mirror lives at `frontend/src/lib/rbac/` with matching primitives, plus shared UI components in `frontend/src/components/ui/`.

## 3. Data model

All new tables live in one Alembic migration, `NNNN_plan4_rbac`.

### 3.1 `departments` (materialized path tree)

```
id            UUID PK
parent_id     UUID FK→departments.id NULL
name          VARCHAR(100) NOT NULL
path          VARCHAR(500) NOT NULL   -- "/UUID/UUID/..." using UUIDs, not names
depth         INT NOT NULL            -- 0 = root
is_active     BOOLEAN NOT NULL DEFAULT TRUE
created_at / updated_at TIMESTAMPTZ NOT NULL DEFAULT now()

UNIQUE (parent_id, name)              -- no duplicate siblings
INDEX (path)                          -- LIKE 'path%' subtree queries
INDEX (parent_id)
```

`path` uses UUIDs so renaming a department does not break scope queries. Scope query for `dept_tree`:
```sql
WHERE target.department_id IN (
  SELECT id FROM departments WHERE path LIKE :user_dept_path || '%'
)
```

### 3.2 `permissions`

```
id            UUID PK
code          VARCHAR(100) NOT NULL UNIQUE  -- "user:create"
resource      VARCHAR(50) NOT NULL          -- "user"
action        VARCHAR(20) NOT NULL          -- "create"
description   VARCHAR(200)                  -- English placeholder; i18n later
created_at    TIMESTAMPTZ NOT NULL DEFAULT now()

CHECK (action IN ('create','read','update','delete','list','export',
                  'approve','reject','publish','invoke'))
INDEX (resource, action)
```

Rows are seeded only via Alembic migrations. No API or CLI creates permissions at runtime.

### 3.3 `roles`

```
id             UUID PK
code           VARCHAR(50) NOT NULL UNIQUE
name           VARCHAR(100) NOT NULL
is_builtin     BOOLEAN NOT NULL DEFAULT FALSE
is_superadmin  BOOLEAN NOT NULL DEFAULT FALSE
created_at / updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

Built-in roles (see §5.3) cannot be deleted. `is_superadmin=TRUE` short-circuits `require_perm`.

### 3.4 `role_permissions`

```
role_id        UUID FK→roles.id ON DELETE CASCADE
permission_id  UUID FK→permissions.id ON DELETE CASCADE
scope          VARCHAR(20) NOT NULL
               CHECK (scope IN ('global','dept_tree','dept','own'))
PRIMARY KEY (role_id, permission_id)
```

Same role × permission can only have one scope (enforced by PK).

### 3.5 `user_roles`

```
user_id        UUID FK→users.id ON DELETE CASCADE
role_id        UUID FK→roles.id ON DELETE CASCADE
granted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
granted_by     UUID FK→users.id NULL
PRIMARY KEY (user_id, role_id)
```

### 3.6 `users` modification

```sql
ALTER TABLE users
  ADD COLUMN department_id UUID NULL REFERENCES departments(id) ON DELETE SET NULL;
CREATE INDEX ix_users_department_id ON users(department_id);
```

## 4. Core utilities

### 4.1 `ScopeEnum` + priority

```python
class ScopeEnum(str, Enum):
    GLOBAL = "global"
    DEPT_TREE = "dept_tree"
    DEPT = "dept"
    OWN = "own"

_SCOPE_PRIORITY = {GLOBAL: 3, DEPT_TREE: 2, DEPT: 1, OWN: 0}
```

Widest-wins when the same code is granted by multiple roles with different scopes.

### 4.2 `get_user_permissions(db, user) -> dict[str, ScopeEnum]`

Per-request load (no cache — see §5). JOINs `user_roles → role_permissions → permissions`, folds widest-wins. Returns `SUPERADMIN_ALL` sentinel for `user.is_superadmin = TRUE`. Stored on `request.state.permissions` once per request.

### 4.3 `require_perm(code: str)` — FastAPI dependency

```python
@router.delete("/users/{user_id}",
               dependencies=[Depends(require_perm("user:delete"))])
```

Checks that the user has the code at **any** scope. Does NOT check scope — that is the caller's responsibility via `apply_scope` / `load_in_scope`. Superadmin bypasses. Failure → 403 with RFC 9457 `type=permission_denied`.

### 4.4 `apply_scope(stmt, user, code, model)` — query filter

Adds a WHERE clause to a SELECT statement based on the user's widest scope for `code`:

| Scope | Predicate |
|---|---|
| `global` | no-op |
| `dept_tree` | `target.department_id IN (SELECT id FROM departments WHERE path LIKE :user_dept_path || '%')` |
| `dept` | `target.department_id = :user_dept_id` |
| `own` | `target.owner_id = :user_id` (or `target.id = :user_id` for `User`) |

The model must declare a `__scope_map__` classvar:

```python
class User(Base):
    __scope_map__ = {
        ScopeEnum.DEPT_TREE: "department_id",
        ScopeEnum.DEPT: "department_id",
        ScopeEnum.OWN: "id",
    }
```

Missing `__scope_map__` → programming error (not runtime 403) — fail loud.

### 4.5 `load_in_scope(db, model, id, user, code)` — single-row loader

Wraps `select(model).where(id == :id)` + `apply_scope`. Returns the row if in scope, raises 404 if not (not 403 — do not leak existence).

## 5. Permission cache strategy

**Decision: per-request load, no cache.** The JOIN is small, correctness beats staleness, upgrade path is easy (`get_user_permissions` is the single cache-insertion point). Superadmin short-circuits without even the JOIN.

No Redis key, no TTL, no invalidation contract for mutations to manage.

## 6. HTTP endpoints

### 6.1 `GET /me/permissions`

**Auth:** authenticated.
**Response:**
```json
{
  "isSuperadmin": false,
  "permissions": {
    "user:read": "dept_tree",
    "user:list": "dept_tree",
    "department:read": "dept_tree"
  }
}
```

### 6.2 `GET /departments`

**Auth:** authenticated + `department:list`.
**Behavior:** lists departments visible to the caller's scope for `department:list`. Response uses the standard paginated envelope (`PaginatedEndpoint`).

## 7. CLI — `cli rbac ...`

Typer app mounted under `backend/app/cli.py`. Subcommands in `backend/app/cli_commands/rbac.py`:

- `grant-role <email> <role_code>` — adds to `user_roles`. Idempotent. Not-found / already-granted → exit 1 with a clear message.
- `revoke-role <email> <role_code>` — deletes from `user_roles`. Idempotent.
- `list-user <email>` — prints roles + effective permissions map.
- `list-roles` — prints all roles with their permission grants.

Invocation in Docker: `docker compose exec backend uv run cli rbac grant-role user@example.com member`.

## 8. Alembic migration & seed

Single migration `NNNN_plan4_rbac.py`:

**`upgrade()`:**
1. `CREATE TABLE departments, permissions, roles, role_permissions, user_roles`.
2. `ALTER TABLE users ADD COLUMN department_id ...` + index.
3. **Seed permissions** — 15 codes: `user:{create,read,update,delete,list}`, `role:{read,list,assign}`, `department:{create,read,update,delete,list}`, `permission:{read,list}`. Each validated with `PermissionCreate.model_validate(...)` before insert.
4. **Seed roles**:
   - `superadmin` (builtin, is_superadmin=True, no role_permissions rows)
   - `admin` (builtin, all 15 codes at scope=global)
   - `member` (builtin, narrow read-only set)
5. **Seed root department** — `name = env.get("SEED_ROOT_DEPT_NAME", "Root")`, `path = "/{uuid}"`, `depth = 0`.
6. **Promote admin@example.com**: `INSERT INTO user_roles (user_id, role_id) SELECT u.id, r.id FROM users u, roles r WHERE u.email='admin@example.com' AND r.code='superadmin' ON CONFLICT DO NOTHING`.
7. **Assign admin@example.com to root dept**.

**`downgrade()`:** removes all seed data + drops tables in reverse dependency order.

### 8.1 `member` role scope matrix

| code | scope |
|---|---|
| `user:read` | `own` |
| `role:read`, `role:list` | `global` |
| `department:read`, `department:list` | `dept_tree` |
| `permission:read`, `permission:list` | `global` |

A brand-new user with no role assignments has zero permissions by design (safe-by-default).

## 9. Frontend primitives

### 9.1 `PermissionsProvider` (`frontend/src/lib/rbac/PermissionsProvider.tsx`)

Mounts under `AuthProvider`. Caches `{isSuperadmin, permissions}` in React context. Refetch triggers:

1. **Initial fetch** on user-became-authenticated transition.
2. **Route change** via react-router `useNavigation()` idle transition.
3. **Window/tab focus** via `focus` + `visibilitychange` events.
4. **Explicit `refetch()`** exposed for callers (used by admin UI in future plans).

Debounced to at most one request per ~500 ms. Cleared on logout.

### 9.2 `usePermissions()` hook

```ts
const { has, isSuperadmin, isLoading, refetch } = usePermissions();
has("user:delete");                // any scope
has("user:delete", "global");      // requires scope ≥ global
```

Scope comparison uses the same widest-wins ordering as the backend.

### 9.3 `<Gate>` primitive (`frontend/src/components/ui/Gate.tsx`)

```tsx
<Gate permission="user:delete" fallback={null}>
  <Button variant="destructive">Delete</Button>
</Gate>
```

Pure logic wrapper, no visual dependency. `minScope` optional prop.

### 9.4 `<ProtectedByPermission>` route guard

Wraps a route element. Redirects to `/403` if the user lacks the permission. Composable with the existing `<ProtectedRoute>` (auth check).

### 9.5 `/403` page (`frontend/src/pages/ForbiddenPage.tsx`)

Minimal: header, "You don't have access to this page." line, button back to `/`. English copy, `// i18n: todo` markers.

### 9.6 Dashboard debug card

Dev-only (`import.meta.env.DEV`) — renders the current `permissions` map on the dashboard so smoke testing can verify the sync loop end-to-end.

## 10. Audits

### 10.1 `audit_scope.py`

AST-based scan of every `backend/app/modules/*/api.py`. For each route handler, verify that any `select(M)` / `db.get(M, ...)` call on a model with `__scope_map__` is paired with `apply_scope(...)` or `load_in_scope(...)`. Escape hatch: inline `# audit-scope: ignore — <reason>` comment directly above the query.

Exits 0 clean, 1 with offender list. Added to `scripts/audit/run_all.sh`.

### 10.2 `audit_schema_db_consistency.py`

For every Pydantic class in `backend/app/modules/*/schemas.py` named `*Create` or `*Update`, cross-check against the corresponding Alembic migration. Flags mismatches between `Field(..., max_length=N)` and `Column(String(M))`, required vs NULL, pattern vs CHECK.

Exits 0 clean, 1 with mismatch list. Added to `scripts/audit/run_all.sh`.

## 11. Convention doc — 5-layer form consistency

New file `docs/conventions/10-form-consistency.md` codifies the rule: for every form field, the required marker + FE validation + error message + BE validation + DB constraint must all agree. Referenced from `CLAUDE.md`'s convention map.

The convention-auditor subagent's checklist is updated to walk all 5 layers per field for any plan that introduces or modifies a form.

## 12. Test database isolation

### 12.1 New `backend/tests/conftest.py` structure

```python
import os

_test_db = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql+asyncpg://app:app@db:5432/business_template_test",
)
if not _test_db.rstrip("/").endswith("_test"):
    raise RuntimeError(
        f"Refusing to run tests against non-test DB: {_test_db}"
    )
os.environ["DATABASE_URL"] = _test_db
os.environ.setdefault("SECRET_KEY", "x" * 40)
os.environ.setdefault("APP_ENV", "test")
```

### 12.2 Session-scoped DB preparation

A `scope="session"` autouse fixture runs `alembic downgrade base` → `alembic upgrade head` against the test DB once per pytest session.

### 12.3 Per-test transactional rollback

A `db_session` fixture opens a connection, begins a transaction, yields an `AsyncSession` bound to it, and rolls back at teardown. Tests that previously used ad-hoc `create_all` / `drop_all` are migrated to this fixture.

### 12.4 docker-compose addition

Postgres container creates both `business_template` and `business_template_test` on first start via a `backend/scripts/init-multiple-dbs.sh` initdb script.

### 12.5 Plan 3 test migration

The ~6–10 Plan 3 test files that currently implicitly use the dev DB are migrated to the new fixture pattern. Mechanical rewrite; no behavioral change.

## 13. Testing

### 13.1 Backend tests

| Layer | Files |
|---|---|
| Unit — service / folding / deps | `tests/modules/rbac/test_service.py`, `test_require_perm.py`, `test_apply_scope.py`, `test_load_in_scope.py` |
| Integration — endpoints | `tests/modules/rbac/test_api.py`, `test_departments_api.py` |
| CLI | `tests/cli/test_rbac_cli.py` |
| Migration round-trip | `tests/migrations/test_rbac_seed.py` |
| Audit fixtures | `tests/scripts/test_audit_scope.py`, `test_audit_schema_db_consistency.py` |

### 13.2 Frontend tests

| Layer | Files |
|---|---|
| Hook | `src/lib/rbac/__tests__/usePermissions.test.ts` |
| Provider (refresh triggers, debounce) | `src/lib/rbac/__tests__/PermissionsProvider.test.tsx` |
| `<Gate>` | `src/components/ui/__tests__/Gate.test.tsx` |
| Route guard | `src/__tests__/protected-by-permission.test.tsx` |

### 13.3 Smoke test (mandatory before `v0.4.0-rbac` tag)

Run via chrome-devtools MCP:

1. Fresh DB → `docker compose up` → log in as `admin@example.com` → dashboard debug card shows `isSuperadmin: true`.
2. `docker compose exec backend uv run cli rbac grant-role user@example.com member`.
3. Log in as `user@example.com` (second browser profile) → debug card shows `member`'s narrower permission set.
4. `docker compose exec backend uv run cli rbac revoke-role user@example.com member`.
5. In `user@example.com`'s tab, switch away and back → debug card updates within a few seconds (focus-refetch).
6. Navigate directly to `/403` → fallback page renders correctly.
7. `GET /departments` returns seeded root dept for both users with correct scope filtering.

## 14. Dependencies (new)

- **Backend**: `typer` (CLI), no others — SQLAlchemy / Pydantic / Alembic already present.
- **Frontend**: none new — React + react-router + existing context patterns.

## 15. File list

See `design-section-8.4` equivalent — summarized here. Complete list in the plan document produced by `writing-plans` next.

**Backend new:** ~20 files under `app/modules/rbac/`, `app/cli.py`, `app/cli_commands/rbac.py`, one Alembic migration, two audit scripts, matching tests.

**Backend modified:** `app/modules/auth/models.py` (add `__scope_map__`, `department_id` relationship), `app/main.py` (mount router), `pyproject.toml` (add typer), `scripts/audit/run_all.sh`, `tests/conftest.py`.

**Frontend new:** `src/lib/rbac/*`, `src/components/ui/Gate.tsx`, `src/components/ui/ProtectedByPermission.tsx`, `src/pages/ForbiddenPage.tsx`, tests.

**Frontend modified:** `src/App.tsx` (mount `PermissionsProvider`, add `/403` route), `src/pages/DashboardPage.tsx` (dev debug card).

**Docs new/modified:** `docs/conventions/10-form-consistency.md`, `CLAUDE.md` (convention map row), `backend/CLAUDE.md` (test-DB section), `docker-compose.yml`, `backend/scripts/init-multiple-dbs.sh`.

## 16. Rollout

1. Implement per writing-plans plan (next artifact).
2. All automated tests green: `pytest + npm test`.
3. Type check clean: `npm run typecheck`, `uv run ruff check .`.
4. `bash scripts/audit/run_all.sh` — all L1 audits PASS, including new `audit_scope` and `audit_schema_db_consistency`.
5. `convention-auditor` subagent → `VERDICT: PASS`.
6. Chrome MCP smoke test covering §13.3 steps 1–7.
7. Commit, tag `v0.4.0-rbac`.

## 17. Out of scope (tracked in `docs/backlog.md`)

- Admin UI for user/role/permission/department CRUD.
- Real-time permission change propagation (SSE / WebSocket).
- Full i18n (EN → JA).
- Move department subtree.
- LoginPage required-field markers (Plan 3 debt).
- Custom roles / per-user scope overrides.
