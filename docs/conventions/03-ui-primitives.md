# 03 · UI Primitives (shadcn/ui + Tailwind)

## Rule

> **One design-token source. Variants defined once via `cva`. Business pages may only import from `@/components/ui`, `@/components/form`, `@/components/table`, `@/components/layout`.**

## Why

Tailwind alone enables drift — each page uses different `p-4 / py-3 px-5`, different shadows, different radii. Without a primitive layer, AI re-invents button/input styles in every module.

## Layering

```
Design tokens (src/lib/design-tokens.ts)
      │
      ▼
Tailwind config (reads tokens; never hard-codes hex)
      │
      ▼
shadcn/ui primitives (@/components/ui) — Radix + Tailwind + cva
      │
      ▼
Business pages (@/modules/*) — compose primitives, no raw CSS
```

## Do

- Import only from the facade dirs listed in the Rule.
- Extend `@/components/ui/Button.tsx` by adding a new cva variant, NOT by adding className overrides at call sites.
- Use Tailwind utilities only for **layout / spacing / flex / grid** in page composition.

## Don't

- Import `@radix-ui/*` directly in a page.
- Pass className overriding internal Button styles (`<Button className="bg-red-500">` ❌).
- Add new colors / radii / font sizes anywhere except `src/lib/design-tokens.ts`.
- Copy a shadcn/ui component into `@/modules/...` — always into `@/components/ui/`.

## Mechanical enforcement

- `scripts/audit/audit_mui_imports.sh` — also scans for `@radix-ui/*` imports outside `src/components/ui/`
- eslint rule (Plan 2): forbid className on components from `@/components/ui` beyond a small allowlist (`w-*`, `h-*`, positioning classes)
- CI: `tailwind.config.ts` must reference `tokens` export from `design-tokens.ts` (audit script)
