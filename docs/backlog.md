# Deferred Work Backlog

Tracks "do later / V-next" features and improvements for this project. Whenever a plan explicitly defers work during design or implementation ("V1 won't do this, save for later"), add an entry here so it doesn't get forgotten.

**Entry format** (newest on top):
- Title + deferred date
- Source plan
- Why deferred
- Rough work estimate
- Dependencies / prerequisites

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
