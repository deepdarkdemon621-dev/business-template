# 99 · Anti-laziness Checklist

Living document. When a new AI-laziness pattern is observed, add a row here with both symptom and mechanical interception.

| # | Pattern | Symptom | Interception |
|---|---|---|---|
| 1 | **FE-side pagination** | `.slice(start, end)` in a page component | `<DataTable>` accepts no `paginationMode` toggle (server-only); list API never returns bare arrays. `audit_pagination_fe.sh`. |
| 2 | **FE-side filter/search** | Full fetch + `.filter()` / `.includes()` | Same as 1 + BE supports `?q=` / field filters. `audit_listing.py` flags endpoints returning all rows. |
| 3 | **N+1 query** | `for obj in list: obj.related` | Require `selectinload` / `joinedload` on relations used in list endpoints; slow-query log in dev; `audit_n_plus_one.py` (Plan 5). |
| 4 | **Missing index** | New filter column has no index | Alembic migration review checklist (PR template) + `audit_migration.py` (Plan 3). |
| 5 | **Swallowed exception** | `except: pass` or `except Exception: pass` | `audit_except.sh` — CI fails. |
| 6 | **Hardcoded magic value** | `if role == "admin":` in code | Use `Role.ADMIN` enum; `audit_magic_strings.py` (Plan 3). |
| 7 | **Missing transaction** | Multiple writes without `async with session.begin()` | Service base class enforces wrapper (Plan 2). |
| 8 | **Unauthorized endpoint** | New router fn with no `require_perm` / `public=True` | `audit_permissions.py` — CI fails. |
| 9 | **Mock data in build** | `MOCK_USERS = [...]` imported in prod code | `audit_mock_leak.sh` — `MOCK_` pattern forbidden outside `tests/`. |
| 10 | **TODO merged to main** | `# TODO: fix later` | `audit_todo.sh` — new TODOs require PR ack. |
| 11 | **Token in localStorage** | `localStorage.setItem("token", ...)` | `audit_storage.sh` (Plan 3) — forbid `localStorage.setItem` of auth keys; must use `sessionStorage` or httpOnly cookie. |
| 12 | **ORM leak in response** | Returning SQLAlchemy objects without Pydantic response model | FastAPI `response_model=` required; `audit_response_model.py` (Plan 2). |

## How to add an entry

1. PR adding the row above
2. PR must include the interception mechanism (script, lint rule, test)
3. `scripts/audit/run_all.sh` must invoke it

A new entry without mechanical interception is **not** a rule — it's just documentation, and gets added to `docs/review-checklist.md` instead.
