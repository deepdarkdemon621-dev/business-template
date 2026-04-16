# frontend/ — Agent guide

Vite + React 19 + TypeScript + Tailwind + shadcn/ui + RHF + ajv. No Next.js, no MUI.

## Layout (read `docs/conventions/08-naming-and-layout.md`)

```
src/
├── api/            axios client + generated types (DO NOT EDIT generated/)
├── lib/            design-tokens, ajv, auth, utils
├── components/
│   ├── ui/         shadcn facade — import only from here in pages
│   ├── form/       FormRenderer, Field, FieldRegistry
│   ├── table/      DataTable (server pagination only)
│   └── layout/     AppShell, Sidebar, TopBar
└── modules/        feature dirs mirroring backend modules/
```

## Non-negotiables

### UI primitives (03)
- Only import from `@/components/{ui,form,table,layout}` in pages.
- Never `import * from "@radix-ui/..."` in a page. Never `import "@mui/material"` anywhere.
- Variants via `cva`, not ad-hoc className.

### Design tokens
- `src/lib/design-tokens.ts` is the only place colors/spacing/radii are defined. `tailwind.config.ts` reads from it.

### Forms (04)
- Every form is `<FormRenderer schema={...} />`.
- No hand-assembled forms with `<input>` / `<TextField>` in pages.
- No Zod / Yup. ajv only (registered in `@/lib/ajv.ts`).

### Tables
- All list views use `@/components/table/DataTable`. Server-side pagination, sort, filter.
- Never `.slice(start, end)` in a page.

### Auth (06)
- axios interceptor (`@/api/client.ts`) owns all 401 handling; business code doesn't touch 401.
- Access token in memory / sessionStorage. Never `localStorage`.
- Route guards via `<RequirePermission />` wrapper (Plan 3).

### Types
- API types from `src/api/generated/` — never hand-write an API type.
- Run `npm run typecheck` — zero errors or CI fails.

### No-go
- Raw `fetch()` — use axios from `@/api/client.ts`.
- `any` / `@ts-expect-error` without a comment justification.
- Inline styles or arbitrary Tailwind values (`[#fff]`, `[32px]`) — use tokens.

## Commands

```bash
cd frontend
npm install
npm run dev         # vite dev server
npm run build       # prod bundle
npm run typecheck
npm run lint
npm test            # vitest
```
