# business-template — Agent guide

Generalized business back-office template (OA / approval systems).

## Required reading before editing anything

Read in this order when you start a session:

1. This file
2. `docs/conventions/08-naming-and-layout.md` — where things live
3. Any `docs/conventions/NN-*.md` relevant to your change (see map below)
4. Module-local `CLAUDE.md` where you're editing

## Convention map

| Touching… | Read |
|---|---|
| Pydantic model / validation | `01-schema-validation.md` |
| Delete / state transition | `02-service-guards.md` |
| FE styling or component | `03-ui-primitives.md` |
| Form rendering / validation UX | `04-forms.md` |
| Endpoint / response shape | `05-api-contract.md` |
| Auth / session / password | `06-auth-session.md` |
| Permissions / data scope | `07-rbac.md` |
| Directory / naming | `08-naming-and-layout.md` |
| **Before claiming done** | `99-anti-laziness.md` |

## Hard rules (quick reference — details in convention docs)

- **No hand-written JSON Schema.** Pydantic only.
- **No bare `.all()` / client pagination.** Use `paginate()` / `<DataTable server>`.
- **No inline permission checks.** Use `require_perm` + `apply_scope`.
- **No `except: pass`.** Ever.
- **No MUI / Radix directly in pages.** Only via `@/components/ui/`.
- **No token in `localStorage`.** sessionStorage or httpOnly cookie.

Full enforcement: `scripts/audit/run_all.sh`.

## Before marking a feature complete

1. All tests green: `cd backend && uv run pytest && cd ../frontend && npm test`
2. Types clean: `npm run typecheck`
3. Lint clean: `uv run ruff check . && npm run lint`
4. L1 audits pass: `bash scripts/audit/run_all.sh`
5. **Invoke `convention-auditor` subagent** → `VERDICT: PASS`
6. Only then mark the feature done / open PR

## Dev commands

```bash
# Boot the full stack
docker compose up -d

# Backend shell
docker compose exec backend bash

# Backend tests
docker compose exec backend uv run pytest

# Frontend tests
cd frontend && npm test

# Run all audits
bash scripts/audit/run_all.sh

# Apply migrations
docker compose exec backend uv run alembic upgrade head
```

## Docs

- Specs: `docs/superpowers/specs/`
- Plans: `docs/superpowers/plans/`
- Conventions: `docs/conventions/`
- Auditor subagent: `.claude/agents/convention-auditor.md`
