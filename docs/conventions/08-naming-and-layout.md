# 08 · Naming & Layout

## Monorepo structure

```
business-template/
├── backend/                 FastAPI service
├── frontend/                Vite SPA
├── docker/                  Dockerfiles & nginx config
├── docs/                    specs, plans, conventions
├── scripts/audit/           L1 audit scripts
├── .claude/agents/          L2 audit subagent
├── .github/workflows/       CI
└── docker-compose.yml       dev orchestration
```

## Backend: feature-first

```
backend/app/
├── main.py
├── core/                    infra: config, auth, guards, form_rules, pagination, ...
└── modules/
    ├── _template/           copy-source for new modules
    ├── auth/
    ├── user/
    ├── department/
    └── <feature>/
        ├── models.py        SQLAlchemy ORM
        ├── schemas.py       Pydantic IO
        ├── service.py       business logic
        ├── router.py        FastAPI endpoints
        └── crud.py          query helpers
```

**Rule:** one feature = one module directory. New feature → copy `_template/` to `modules/<name>/`.

**Rule:** `app/api/v1.py` only aggregates routers. No business code there.

## Frontend: feature-first, mirrors backend

```
frontend/src/
├── App.tsx, main.tsx, router.tsx
├── api/
│   ├── client.ts            axios + interceptors (Plan 3)
│   └── generated/           openapi-typescript output — DO NOT EDIT
├── lib/
│   ├── design-tokens.ts     SSOT for colors/spacing/radii (read by tailwind.config.ts)
│   ├── ajv.ts               ajv instance + rule registrations (Plan 2)
│   ├── auth/                AuthProvider, useAuth, usePermissions (Plan 3)
│   └── utils.ts
├── components/
│   ├── ui/                  shadcn/ui facade (ONLY import source for primitives)
│   ├── form/                FormRenderer, Field, FieldRegistry
│   ├── table/               DataTable (server pagination only)
│   └── layout/              AppShell, Sidebar, TopBar
└── modules/
    ├── auth/
    ├── user/
    └── <feature>/           pages + module-local components + hooks
```

**Rule:** frontend `modules/<feature>/` names match backend `modules/<feature>/`. One-to-one.

## Naming

| Context | Convention | Example |
|---|---|---|
| Python modules, files | snake_case | `audit_log.py` |
| Python classes | PascalCase | `AuditLog` |
| Python funcs/vars | snake_case | `get_user_by_id` |
| TypeScript files (component) | PascalCase | `UserTable.tsx` |
| TypeScript files (hook/util) | camelCase | `useAuth.ts`, `formatDate.ts` |
| TypeScript vars/funcs | camelCase | `currentUser` |
| TypeScript types/interfaces | PascalCase | `UserRow` |
| URLs (routes) | kebab-case, plural nouns | `/api/v1/audit-logs` |
| JSON fields (wire) | camelCase | `{ createdAt, fullName }` |
| DB columns | snake_case | `created_at`, `full_name` |
| Permission codes | `resource:action` | `audit-log:list` |
| CSS class extension | Tailwind utility | `flex gap-4 p-4` |

## CLAUDE.md hierarchy

1. `CLAUDE.md` (root) — entry, required-reading index
2. `backend/CLAUDE.md`, `frontend/CLAUDE.md` — layer rules
3. `app/core/CLAUDE.md`, `components/ui/CLAUDE.md`, `components/form/CLAUDE.md` — local constraints

CLAUDE.md files are **short** (≤200 lines). They reference `docs/conventions/*` for detail. Never duplicate convention content.

## Mechanical enforcement

- `scripts/audit/audit_layout.py` (Plan 2) — reject modules that skip any of the 5 standard file names
- CI: new modules must include the 5 canonical files (even if stub)
