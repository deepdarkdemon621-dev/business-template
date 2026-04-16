# components/ui — Primitive facade

This is the **only** place shadcn/ui primitives live. Business code under `src/modules/*` may import from here, but must not import from `@radix-ui/*` directly.

## Adding a new primitive

1. Use shadcn CLI: `npx shadcn add <component>` — lands here.
2. Wrap it if variants are needed (`cva` — no className overrides at call sites).
3. Ensure it reads colors/radii/spacing from `src/lib/design-tokens.ts` (via Tailwind config).
4. Add a minimal Vitest smoke test.

## Extending an existing primitive

- Add a new `cva` variant, NOT a new prop or a className.
- If you can't express it as a variant, reconsider: maybe it's a new primitive, not a variant.

## What does NOT belong here

- Business-specific components (e.g., `UserAvatar` with specific avatar logic) — those go in `modules/user/`.
- Form-specific fields — those go in `components/form/fields/`.
