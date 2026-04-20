# Deferred Work Backlog

Tracks "do later / V-next" features and improvements for this project. Whenever a plan explicitly defers work during design or implementation ("V1 won't do this, save for later"), add an entry here so it doesn't get forgotten.

**Entry format** (newest on top):
- Title + deferred date
- Source plan
- Why deferred
- Rough work estimate
- Dependencies / prerequisites

---

## 2026-04-21 — Migrate `UserEditPage` to `<FormRenderer>` pipeline

- **Source**: Plan 5 convention-auditor finding; user accepted deferral at tag time
- **Context**: Plan 5 shipped `UserEditPage.tsx` with hand-rolled `<Input>`/`<Label>` trees for both create and edit modes. Convention 04 mandates every form go through `<FormRenderer schema={...} />` driven by ajv + JSON Schema + `x-rules`; every other form in the app (Login, PasswordChange, PasswordReset) already does. UserEditPage is the sole outlier and a real convention-04 violation that was deferred to keep Plan 5 prototype scope shippable.
- **What's needed**:
  - Derive a JSON Schema for `UserCreateIn` / `UserUpdateIn` (either hand-authored or lifted from generated OpenAPI)
  - Replace the form body with `<FormRenderer>`; surface server-side `ProblemDetails.errors` via `setFieldErrors`
  - Keep `<RoleAssignmentPanel>` as-is (it's not a form field — it's a role-diff panel); render it alongside the renderer in edit mode
  - Register `passwordPolicy` custom rule in `@/lib/ajv.ts` if not already present
  - Update `UserEditPage.test.tsx` to interact via the rendered fields (labels should still match the Chinese strings)
- **Work estimate**: ~1 small plan's worth (~half-day). Touches UserEditPage + test + potentially one ajv rule registration.
- **Dependencies**: none. Best landed before/with the Role-CRUD plan so both admin forms follow the same pattern from day 1.

---

## 2026-04-20 — `LastOfKind` race condition under READ COMMITTED

- **Source**: Plan 5 Task A2 code quality review
- **Context**: `LastOfKind.check` reads the count of role holders, then the service layer deletes the `UserRole` row. Under PostgreSQL's default `READ COMMITTED` isolation, two concurrent admin sessions can both observe "2 superadmins", both pass the check, and both commit a removal — leaving zero. Rare in practice (concurrent admin ops on the same role), but the window exists.
- **What's needed**:
  - Either: take a row-level lock inside `LastOfKind.check` via `SELECT ... FOR UPDATE` on `Role` (serializes concurrent mutations of that role's members)
  - Or: bump `strip_role` operations to `SERIALIZABLE` isolation (highest correctness, highest overhead)
  - Or: add a DB CHECK constraint / trigger enforcing "at least one superadmin"
- **Work estimate**: ~10 LOC + integration test with two concurrent sessions
- **Dependencies**: none. Land alongside any isolation-level revisit (e.g. an audit-log or workflow plan that also cares about consistency).

---

## 2026-04-20 — `last_login_at` field on User (operational visibility)

- **Source**: Plan 5 design discussion (D3); scoped out of prototype
- **Context**: User list page lacks "last login" visibility. Useful for spotting dormant accounts and stale permissions.
- **What's needed**:
  - Alembic migration: add `users.last_login_at TIMESTAMPTZ NULL` + index
  - `modules/auth/service.py`: on successful token issuance, `UPDATE users SET last_login_at = now()`
  - `UserOut` schema + list page column + sort support
- **Work estimate**: ~15 LOC + 1 migration + 1 test. Trivial.
- **Dependencies**: none. Best bundled with Role-CRUD or Audit-log plan so we only touch the user list page once more.

---

## 2026-04-20 — Plan 5 admin-CRUD scope extensions (deferred from prototype)

- **Source**: Plan 5 design discussion; user chose minimal prototype scope
- **Context**: Plan 5 ships a working prototype (User CRUD + Role assignment + DataTable + AppShell primitives). These extensions were scoped out to keep the first admin UI shippable, but must follow once the prototype validates the stack end-to-end.
- **What's needed** (each can be its own small plan):
  - **Department tree CRUD UI** — create/rename/move/delete nodes, parent picker, materialized-path integrity; FE tree component + backend `move_department` from existing backlog entry
  - **Role CRUD + RolePermission editor** — create/edit roles, grant/revoke permissions with scope picker (global / dept_tree / dept / own); permission matrix UI
  - **Audit log viewer** — filterable list of mutation events (who / when / what resource / before-after diff), per-resource drill-down
  - **Session management admin view** — view all active sessions across users, revoke remotely (extends existing `/me/sessions` to admin-scoped endpoint)
- **Work estimate**: each ~0.5–1 plan's worth. Best sequenced: Role editor → Department tree → Audit viewer → Session admin.
- **Dependencies**: Plan 5 prototype complete (DataTable + AppShell primitives available). Department tree needs `move_department` backend op (itself already backlogged).

---

## 2026-04-17 — LoginPage missing required-field markers (5-layer form consistency debt)

- **Source**: Plan 3 retro; deferred during test phase
- **Context**: `LoginPage` labels for Email and Password don't show a red asterisk, violating layer 1 of the 5-layer form consistency rule. BE validation, FE validation, and DB constraints are in place — only the visible marker is missing.
- **What's needed**:
  - Add `required` visual indicator to Email + Password labels
  - Verify on-blur / on-submit field-specific error messages render correctly (red border + red message under the field, not a generic form-level error)
  - Mirror check for `ResetPasswordPage` + `ChangePasswordPage` while there
- **Work estimate**: trivial — ~30 minutes including tests
- **Dependencies**: none. Fix during the next plan that touches auth UI (Plan 5 AppShell polish pass or first admin UI plan, whichever comes first).

---

## 2026-04-17 — Real-time permission change propagation (server push)

- **Source**: Plan 4 (RBAC) design
- **Context**: V1 syncs FE permissions via initial fetch + route change + window focus + explicit `refetch()`. That covers almost all realistic sessions — but a user idle on a single tab can see up to ~seconds of staleness if an admin just changed their roles.
- **What's needed**:
  - Server push channel (SSE preferred over WebSocket — simpler, auto-reconnect, one-way fits the use case)
  - BE: on role grant/revoke/role-permissions change, publish `user:{id}:permissions-changed` event
  - FE: `PermissionsProvider` subscribes to the current user's channel and calls `refetch()` on event
  - Reconnection + backfill: if FE disconnects and reconnects, refetch once to recover missed events
- **Work estimate**: small-to-moderate. ~1 day for SSE endpoint + Redis pub/sub + FE EventSource subscriber + tests. Nice to have infrastructure: lets us push other per-user notifications later (session revoked, password changed elsewhere).
- **Dependencies**: admin UI for role assignment must exist first (there's nothing to push in V1 since there's no runtime way to change permissions outside CLI). Sensible timing: alongside the first admin UI plan.

---

## 2026-04-17 — Full i18n implementation (EN → JA switch)

- **Source**: Plan 4 design discussion
- **Context**: Product targets Japanese users. Dev happens in English; final UI must render in Japanese.
- **What's needed**:
  - Frontend i18n framework (proposal: `react-i18next` or `@lingui/react`) + locale resource files
  - Backend i18n for validation messages, email templates, error `detail` fields (via `Accept-Language` header)
  - Seed data localization: `role.name`, `department.name`, `permission.description` currently default to English placeholders → Japanese equivalents
  - Date/time formatting: JST timezone + Japanese conventions where shown
  - Decision point: bilingual (EN + JA) or JA-only ship? Defer decision but design for bilingual since retrofit cost is high
- **Work estimate**: moderate — probably its own plan. Touches every component with user-facing copy. Migrations needed for any `description` / `name` columns that become translated.
- **Dependencies**: none blocking; can start any time. Best timing: after admin UI plan (so we i18n once, not twice).

---

## 2026-04-17 — Move department subtree

- **Source**: Plan 4 (RBAC) design
- **Why deferred**: V1 has no admin UI, so even if the backend supported it, only CLI callers could invoke it. The materialized-path schema already supports this operation — adding it later requires no migration. Plan 4 scope is already large (5 tables + core utilities + audit + seed); the move operation fits better alongside an eventual "Org-chart management" feature.
- **Work estimate**: ~15 LOC for `move_department(dept_id, new_parent_id)` + 3-4 tests
  - Bulk `path` rewrite for descendants (`UPDATE ... SET path = replace(path, old_prefix, new_prefix) WHERE path LIKE old_prefix || '%'`)
  - Sync `depth` updates
  - Cycle detection (cannot move a node under its own descendant)
  - Regression test that `apply_scope(dept_tree)` still resolves correctly after a move
- **Dependencies**: none (schema is ready). Recommend bundling with the Org-chart management UI as its own plan.

---
