# Plan 8 — Audit Log Viewer (+ `users.last_login_at` + dead-code cleanup)

**Date:** 2026-04-24
**Target release:** `v0.8.0-audit-log`
**Predecessor:** `v0.7.0-role-crud`

## Goal

1. Persist a compliance-grade audit trail of admin mutations and authentication events to a new `audit_events` table, written synchronously from the service layer in the same DB transaction as the mutation itself.
2. Provide a superadmin-only viewer at `/admin/audit` — list page with structured filters (date range, event type, action, actor, resource), detail drawer with a diff view (create=snapshot, delete=snapshot, update=field-level delta).
3. Capture actor context (user id, IP, user-agent) via a request-scoped contextvar so service code doesn't have to thread it through every call.
4. Replace Plan 7's `logger.info("role.created", ...)` structured-log emissions with `audit.record(...)` calls — `logger.info` stays for operational logs only; audit events become the single source of truth for business events.
5. Enforce 1-year retention via an externally-invoked CLI pruning command (`python -m app.cli audit prune`), with chunked deletes so pruning a huge table doesn't lock the writer queue.
6. **Bundled from backlog:** add `users.last_login_at` (updated on successful login), surface it as a column on `UserListPage`; delete the dead-code `list_departments` function flagged by the Plan 7 convention-auditor review.

## Non-Goals (later plans)

- Export endpoint (CSV/JSON audit dump) — add if/when someone asks.
- Full-text search across the JSONB `before`/`after`/`changes` payload — structured filters cover realistic use cases; GIN index can be added later.
- Department-scoped audit reads (`audit:read @ dept:{id}`). V1 is superadmin-only at `audit:read @ global`; dept-scoped variant is YAGNI until a dept-admin workflow requires it.
- Intrusion-detection-style events (permission-check denials, every failed admin action). Those belong in a security-monitoring plan.
- Real-time push of new audit events to the viewer (SSE) — list page is polled on navigation/focus like every other admin list.
- In-process scheduler (APScheduler, arq). Pruning runs as an external CLI command invoked by OS cron or a compose one-shot job.
- `LastOfKind` READ COMMITTED race fix — separate backlog item, not audit-related.
- FormRenderer `StringField` required-marker asterisk, LoginPage/ResetPasswordPage required markers — form-consistency debt, belongs in a form-polish plan.
- i18n EN→JA cutover. Event `summary` strings are rendered server-side so they're i18n-ready later, but no locale switching in V1.

## Architecture Overview

One new module + small hooks into existing modules + bundled debts in the modules already touched.

1. **New module `app/modules/audit/`** — data model, pydantic schemas, CRUD helpers (via `paginate()`), `AuditService` with one method per event type, router with `GET /audit-events` and `GET /audit-events/{id}`, and a request-scoped `audit_context` contextvar.
2. **Hooks into existing service layers** — `UserService`, `RoleService`, `DepartmentService`, `AuthService` each call the appropriate `audit.xxx()` method at their mutation boundaries. Same SQLAlchemy `session`, same outer transaction → if the mutation rolls back, so does the audit row.
3. **CLI: `app/cli/audit.py`** — registered as a `typer` subcommand. Chunked delete loop with per-chunk commit; emits a self-audit event `audit.pruned`.
4. **Frontend `src/modules/audit/`** — mirrors `src/modules/rbac/` shape. `AuditLogPage` uses the same `<DataTable server>` template and `useServerTable` hook as `UserListPage` / `RoleListPage` — per the list-page consistency rule, no divergence from that template. Detail drawer uses a new `<Sheet>` primitive; date range uses a new `<DateRangePicker>` primitive.
5. **Bundled in this plan:**
   - `users.last_login_at` column + index + wiring in the login success path + column on `UserListPage`.
   - Delete `rbac/crud.py::list_departments` (unwired, has an unbounded `.scalars().all()` that a previous auditor flagged).

## Data Model

### Migration 0007

**New table `audit_events`:**

```sql
CREATE TABLE audit_events (
  id               BIGSERIAL     PRIMARY KEY,
  occurred_at      TIMESTAMPTZ   NOT NULL,
  event_type       VARCHAR(64)   NOT NULL,
  action           VARCHAR(32)   NOT NULL,
  actor_user_id    BIGINT        NULL REFERENCES users(id) ON DELETE SET NULL,
  actor_ip         INET          NULL,
  actor_user_agent VARCHAR(512)  NULL,
  resource_type    VARCHAR(32)   NULL,
  resource_id      BIGINT        NULL,
  resource_label   VARCHAR(255)  NULL,
  before           JSONB         NULL,
  after            JSONB         NULL,
  changes          JSONB         NULL,
  metadata         JSONB         NULL
);

CREATE INDEX ix_audit_events_occurred_at_desc ON audit_events (occurred_at DESC, id DESC);
CREATE INDEX ix_audit_events_actor            ON audit_events (actor_user_id, occurred_at DESC);
CREATE INDEX ix_audit_events_resource         ON audit_events (resource_type, resource_id, occurred_at DESC);
CREATE INDEX ix_audit_events_action           ON audit_events (action, occurred_at DESC);
```

**Denormalized `resource_label`:** when a role/user/dept is deleted, the UI should still show `"角色: 财务经理"` on the event row instead of a broken FK lookup. Populated at write time from the entity's display name.

**`actor_user_id` ON DELETE SET NULL:** if a user is later hard-deleted, their audit history survives as "anonymized" events rather than triggering cascade deletion of the audit trail.

**Permission seed (same migration):**

```sql
INSERT INTO permissions (id, code, resource, action, description) VALUES
  (gen_random_uuid(), 'audit:read', 'audit', 'read', 'Read audit events');

INSERT INTO role_permissions (role_id, permission_id, scope)
SELECT r.id, p.id, 'global'
FROM   roles r, permissions p
WHERE  r.code = 'superadmin'
  AND  p.code = 'audit:read';
```

**Note:** seeding a grant on `superadmin` is belt-and-suspenders — `superadmin` short-circuits all permission checks by design. The seed is so the permission is discoverable in the role-permission matrix and to keep the data model consistent.

**`users.last_login_at` addition (same migration):**

```sql
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMPTZ NULL;
CREATE INDEX ix_users_last_login_at ON users (last_login_at DESC NULLS LAST);
```

**Downgrade:** drop the column + index; delete the seed permission + grant; drop `audit_events` table.

## Event Taxonomy

Admin mutations:
- `user.created`, `user.updated`, `user.deleted`
- `role.created`, `role.updated`, `role.deleted`, `role.permissions_updated`
- `user.role_assigned`, `user.role_revoked`
- `department.created`, `department.updated`, `department.deleted`

Auth:
- `auth.login_succeeded`, `auth.login_failed`, `auth.logout`
- `auth.password_changed`
- `auth.password_reset_requested`, `auth.password_reset_consumed`
- `auth.session_revoked`

Self:
- `audit.pruned` — emitted by the pruning CLI; carries `metadata = {"cutoff": "...", "deleted_count": N}`.

`action` column is the coarse verb used by filters: `create` / `update` / `delete` / `login` / `logout` / `login_failed` / `password_changed` / `password_reset_requested` / `password_reset_consumed` / `session_revoked` / `pruned`.

## Backend Components

### `modules/audit/`

- `models.py` — `AuditEvent` SQLAlchemy model.
- `schemas.py` — `AuditEventOut` (list shape, actor joined in, `summary` rendered), `AuditEventDetailOut` (adds `before`/`after`/`changes`/`metadata`), filter DTOs.
- `crud.py` — `create_event(session, fields)`, `list_events(session, filters, page)` via existing `paginate()` helper, `get_event(session, id)`.
- `service.py` — `AuditService` with one method per event type (explicit named API, see section "AuditService API" below) + private `_record()` low-level writer + `_diff_dict(before, after)` helper + `_strip_sensitive(payload)` filter.
- `summaries.py` — `render_summary(event) -> str` dispatch table. One branch per event type. Unit-tested independently.
- `router.py` — two endpoints (see below). Dependencies: `require_perm("audit:read", scope="global")` + `bind_audit_context` (populates contextvar for the request, even though list endpoints don't emit events — the dep is cheap and belongs on every authed route).
- `context.py` — `AuditContext` frozen dataclass `{actor_user_id, actor_ip, actor_user_agent}` + `audit_context: ContextVar[AuditContext | None]`.

### Endpoints

| Method | Path                  | Perm                    | Response                            | Notes |
|--------|-----------------------|-------------------------|-------------------------------------|-------|
| GET    | `/audit-events`       | `audit:read` @ global   | `Page<AuditEventOut>`               | Filters in query string, default sort `-occurred_at`. No server-imposed date-range default — omit `occurred_from`/`occurred_to` to query all retained rows. The 7-day-window default is a FE concern (see frontend section). |
| GET    | `/audit-events/{id}`  | `audit:read` @ global   | `AuditEventDetailOut` (200 or 404)  | Full payload including diff fields. |

No mutation endpoints — audit is append-only via service calls, never via HTTP.

### `AuditEventOut` (list shape)

```python
class AuditActor(BaseModel):
    id: int
    email: EmailStr
    name: str

class AuditEventOut(BaseModel):
    id: int
    occurred_at: datetime
    event_type: str
    action: str
    actor: AuditActor | None
    actor_ip: str | None
    actor_user_agent: str | None
    resource_type: str | None
    resource_id: int | None
    resource_label: str | None
    summary: str    # server-rendered one-liner

class AuditEventDetailOut(AuditEventOut):
    before: dict | None
    after: dict | None
    changes: dict | None
    metadata: dict | None
```

### AuditService API

Called from service layers at mutation boundaries. All methods are synchronous, add rows to the same session the caller is using, and never commit internally.

```python
# Admin mutations
audit.user_created(user)
audit.user_updated(user, changes)                     # changes = {"name": [old, new]}
audit.user_deleted(user_snapshot)
audit.role_created(role)
audit.role_updated(role, changes)
audit.role_deleted(role_snapshot)
audit.role_permissions_updated(role, added, removed)  # lists of {permission_code, scope}
audit.user_role_assigned(user_id, role_id, scope)
audit.user_role_revoked(user_id, role_id, scope)
audit.department_created(dept)
audit.department_updated(dept, changes)
audit.department_deleted(dept_snapshot)

# Auth
audit.login_succeeded(user)
audit.login_failed(email, reason)        # reason ∈ {unknown_email, bad_password, disabled_account, locked}
audit.logout(user)
audit.password_changed(user)
audit.password_reset_requested(user)
audit.password_reset_consumed(user)
audit.session_revoked(user, session_id, by_admin)
```

Each method: reads actor context from the contextvar; builds `before`/`after`/`changes`/`metadata` as appropriate; calls `_strip_sensitive` on all JSON payloads; denormalizes `resource_label` from the entity; calls `crud.create_event(...)`.

### `_strip_sensitive` — security-critical

Recursively walks a dict/list; drops any key whose lowercased name matches `{"password", "password_hash", "token", "refresh_token", "refresh_token_hash", "secret", "access_token", "reset_token", "api_key"}`. Unit-tested end-to-end: generate every event type, assert no forbidden key appears anywhere in the stored JSONB.

### `bind_audit_context` dependency

FastAPI dependency added to every authed route via the existing router-level dependency list. Pulls current user from the existing auth dependency; reads IP from `request.client.host`, replaced with the `X-Forwarded-For` first entry when `TRUSTED_PROXIES` env var lists the upstream; reads `User-Agent` header (truncated to 512). Sets `audit_context` contextvar for the request. Auth endpoints (login/logout/password-reset) bind a partial context (null actor for unauthenticated login).

### Transaction semantics

`audit._record()` does `session.add(audit_event)` without flushing or committing. The outer service-layer transaction commits both mutation + audit atomically. A dedicated test (`test_audit_transactional.py`) forces the outer transaction to raise *after* `audit.record(...)` and asserts the audit row is absent — no phantom audits.

### Pruning CLI

- File: `app/cli/audit.py`, exposing `prune(older_than_days: int = 365)` as a `typer` subcommand under a top-level `app/cli/__main__.py` dispatcher.
- Logic:
  1. Compute cutoff = `now() - interval ':d day'`.
  2. Loop: `DELETE FROM audit_events WHERE occurred_at < :cutoff AND id IN (SELECT id FROM audit_events WHERE occurred_at < :cutoff ORDER BY id LIMIT 10000)`, commit, repeat until 0 rows affected.
  3. Emit `audit.pruned` with `metadata = {"cutoff": ..., "deleted_count": N, "chunks": K}`.
- Docs: `docs/ops/audit-retention.md` explains the policy (1 year), the command, the recommended cron (yearly Jan 1 03:00 UTC, or monthly for smoother disk usage).

### Hooks into existing services

- `UserService.create/update/delete` → `audit.user_created/updated/deleted(...)`.
- `RoleService.create/update/delete` (Plan 7) → replaces `logger.info(...)` with `audit.role_*(...)`; `replace_role_permissions` → `audit.role_permissions_updated(...)`.
- `DepartmentService.create/update/delete` → `audit.department_*(...)`.
- `UserRoleService` (or wherever role assignment lives) → `audit.user_role_assigned/revoked(...)`.
- `AuthService`:
  - Successful login: set `user.last_login_at = now()` **and** call `audit.login_succeeded(user)` in the same transaction.
  - Failed login paths: call `audit.login_failed(email, reason)`.
  - Logout, password change, password reset endpoints: call the matching audit method.

## Frontend Components

### `src/modules/audit/`

- `types.ts` — `AuditEvent`, `AuditEventDetail`, `AuditFilters`.
- `api.ts` — `listAuditEvents(params): Promise<Page<AuditEvent>>`, `getAuditEvent(id): Promise<AuditEventDetail>` using the shared axios wrapper.
- `AuditLogPage.tsx` — list page.
- `components/AuditEventDetail.tsx` — `<Sheet>`-based detail drawer.
- `components/DiffView.tsx` — small component that renders `create` / `delete` / `update` variants (no external diff library).

### Routing & sidebar

- Route `/admin/audit` registered alongside existing `/admin/users`, `/admin/roles`, `/admin/departments`.
- Sidebar entry 审计日志 (EN label `Audit Log`; Japanese later) guarded on `audit:read`. Only superadmin sees it.
- Guard-mismatch note: verify the sidebar entry's guard matches the backend permission code exactly (`audit:read`) — per the Plan 7 smoke-test lesson where a `role:read` / `role:list` mismatch shipped unnoticed.

### `AuditLogPage` — matches `UserListPage` / `RoleListPage` exactly

Per the list-page consistency rule:
- `<DataTable server>` with the same pagination/sort query params, same `useServerTable` hook, same row-hover style.
- Same icon vocabulary for the action column (eye icon for view; no edit/delete since audit is append-only).
- Same filter-bar placement as existing list pages.

Columns:

| # | Header          | Source field            | Notes |
|---|-----------------|-------------------------|-------|
| 1 | Occurred at     | `occurred_at`           | `YYYY-MM-DD HH:mm:ss`; sortable; default sort `-occurred_at`. |
| 2 | Event           | `event_type`            | Colored pill: create=green, update=blue, delete=red, login=gray, login_failed=amber, others=neutral. |
| 3 | Actor           | `actor.name` + `.email` | Two-line cell; dash when null. |
| 4 | Resource        | `resource_type:resource_label` | Dash for pure auth events. |
| 5 | Summary         | `summary`               | Server-rendered one-liner. |
| 6 | IP              | `actor_ip`              | Muted. |
| 7 | Actions         | —                       | Single eye icon → opens detail drawer. |

### Filter bar (above the table, same slot `UserListPage` uses for its filter)

- Date range picker → `occurred_from` + `occurred_to`; default = last 7 days on first visit, persisted to URL query string.
- Event type multi-select (shadcn `<Select>` wrapped in `@/components/ui/select`).
- Action multi-select.
- Actor autocomplete — reuses the existing user-autocomplete used by `RoleAssignmentPanel`.
- Resource filter: resource-type dropdown + resource-id number input (paired).
- "Clear filters" text link returning to defaults.

### `AuditEventDetail` drawer

- shadcn `<Sheet>` (right-drawer). Added as a new primitive at `@/components/ui/sheet.tsx` in this plan.
- Sections:
  - Header: occurred_at, event_type pill, actor (name + email + IP + UA on hover), resource.
  - Summary line.
  - Diff section (`<DiffView>`):
    - `create`: `after` JSON in a `<pre>` with a green left border.
    - `delete`: `before` JSON in a `<pre>` with a red left border.
    - `update`: 2-column table (field | old → new) using the `@/components/ui/table` primitive, not bare `<table>`.
    - Auth events (null `changes`): hide diff; show `metadata` JSON if present.

### New UI primitives (added in this plan)

- `@/components/ui/sheet.tsx` — shadcn Sheet. First use is here; intended for general reuse (future "quick-peek" detail views).
- `@/components/ui/date-range-picker.tsx` — shadcn Calendar + Popover composition. First use is here; reusable by future reporting/analytics pages. Must support keyboard navigation and clear-selection UX per shadcn defaults.

### Bundled: `UserListPage` gains a "Last login" column

- Add `last_login_at: datetime | null` to `UserOut` (and detail shape if returned).
- `UserListPage` adds a sortable "Last login" column rendering `YYYY-MM-DD HH:mm` or muted "Never" for null. No filter in V1.
- Column ordering per list-page consistency: insert in a logical position matching the existing columns' semantics (between account-status columns and the actions column); explicit placement decided at implementation time against the current column set.

## Testing Strategy

### Backend unit (`backend/tests/modules/audit/`)

- `test_audit_service.py` — one test per service method; asserts row shape + `changes` correctness + `before`/`after` variant correctness for create/update/delete.
- `test_audit_sensitive_field_stripping.py` — generates events from every method; walks every JSONB payload; asserts no key matches the sensitive-field regex. **Security-critical; do not skip.**
- `test_audit_transactional.py` — mutation raises after `audit.record(...)` → assert audit row rolled back with the mutation.
- `test_audit_context.py` — authed request → contextvar populated; unauthed login → null actor but IP/UA captured; `X-Forwarded-For` + `TRUSTED_PROXIES` → correct IP.
- `test_audit_summaries.py` — each event type → correct `summary` string.

### Backend API (`backend/tests/api/`)

- `test_audit_endpoints.py`:
  - Without `audit:read` → 403 ProblemDetails.
  - With `audit:read`:
    - Default sort, pagination envelope matches shape used by `/users` / `/roles`.
    - Each filter (date, event_type, action, actor, resource_type+id) narrows correctly.
    - Sort accepts `occurred_at`, `-occurred_at`, `id`, `-id`; rejects unknown keys.
    - List response excludes `before`/`after`/`changes`/`metadata`.
  - `GET /audit-events/{id}` → full payload; 404 for unknown id; 403 without perm.

### Integration (event emission)

- `test_audit_integration.py` drives each admin endpoint and each auth endpoint end-to-end; asserts exactly one audit event per mutation with the expected shape. Special: login → `users.last_login_at` updated in the same transaction as `audit.login_succeeded`.

### Pruning

- `test_audit_prune_cli.py`:
  - Seed 100 events across a 2-year range → `prune --older-than-days 365` → correct count deleted, correct cutoff, `audit.pruned` self-event emitted with right metadata.
  - Chunked deletion: seed >CHUNK_SIZE rows → assert multiple commits (transaction-count spy), no long single-tx lock.

### Frontend (`frontend/src/modules/audit/__tests__/`)

- `AuditLogPage.test.tsx` — DataTable renders; sidebar entry gated; default filters (last 7 days) applied; column set matches spec.
- `AuditEventDetail.test.tsx` — correct diff variant rendered per event type; auth events hide diff section.
- `DiffView.test.tsx` — create/delete/update variants render correctly.
- Permission-gate test: non-superadmin user → sidebar entry absent; direct URL visit → redirect.

### E2E smoke (`scripts/smoke/plan8-smoke.mjs`)

Matches Plan 7's smoke shape. 8 steps: login as superadmin → sidebar entry visible → page loads → default 7-day filter → mutate a user in another tab → refresh → new event appears → click eye icon → drawer + diff → filter by event_type → logout → login as non-superadmin → sidebar entry absent + direct URL blocked.

### Convention gate (before tagging `v0.8.0-audit-log`)

- Backend + frontend tests green.
- `uv run ruff check .` + `npm run typecheck` + `npm run lint` clean.
- `bash scripts/audit/run_all.sh` (L1 audits) clean.
- `convention-auditor` subagent returns `VERDICT: PASS`.
- Browser smoke-test passes per the "smoke-test before complete" rule.

## Convention Deviations (intentional, documented)

1. **Audit table grows unbounded until externally pruned.** Most tables in this project are naturally bounded. Retention is documented in `docs/ops/audit-retention.md` + enforced by the CLI, not by app-level logic.
2. **`GET /audit-events` list response omits `before`/`after`/`changes`/`metadata`.** Every other list endpoint returns the full entity shape. Audit list is intentionally lean because diff payloads can be multi-KB and are only needed in the detail drawer.
3. **`bind_audit_context` dependency attached broadly.** The dep runs even on routes that don't emit audit events (read-only GETs). Justification: cheap, and it lets any future audit emission from a read-only codepath work without retrofitting the dependency graph. Documented in `modules/audit/context.py` module docstring.

## Risks & Mitigations

- **Sensitive data leaking into audit JSONB.** Mitigated by the `_strip_sensitive` filter and the end-to-end coverage test that generates every event type and greps the resulting payloads.
- **Actor contextvar cross-contamination across async tasks.** FastAPI's request-scoped context handling makes this safe for the main request lifecycle, but any `asyncio.create_task(...)` inside a handler would see the contextvar snapshot — not share it. No such detached tasks exist in the current codebase; a comment in `context.py` warns future contributors.
- **Pruning CLI run under heavy write load.** Chunked delete (10k rows per commit) bounds lock duration. Documented in the ops doc; recommended to run during a low-traffic window.
- **Dead-code `list_departments` deletion could surface hidden callers.** Mitigated by grep-verification (no callers anywhere in `app/`, `frontend/`, or tests) before deletion; and the convention-auditor gate will catch re-introduction.
- **Migration 0007 in one file does three things** (table + permission seed + `last_login_at`). Justified because the plan explicitly bundles them; each change is small and independently downgradable. The migration's `downgrade()` reverses in strict reverse order.

## Dependencies

- Plan 7 (`v0.7.0-role-crud`) shipped and tagged.
- No new Python or npm dependencies required. `typer` is already pinned for other CLI uses.
- New shadcn primitives (`<Sheet>`, `<Calendar>`+`<Popover>` for date range) — these are vendored shadcn patterns, no new npm packages.

## Pre-implementation verifications (do during Step 1 of the plan)

These are details to confirm against the current codebase before wiring audit calls. Neither blocks the design — each has an obvious fallback if the assumption turns out slightly different.

- Confirm `users.email` is the current canonical login identity used by the auth service. If login takes a different field, `audit.login_failed(email, reason)` becomes `audit.login_failed(identifier, reason)` with the same semantics.
- Confirm the existing session-revoke code path (Plan 3 work) and its service method signature so `audit.session_revoked(...)` is called at the right boundary. If no admin-initiated revoke exists yet in V1 (only self-revoke via `/me/sessions`), the `by_admin` flag defaults to `false` and the event still captures self-revocations correctly.
