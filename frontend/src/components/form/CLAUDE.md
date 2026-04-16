# components/form — JSON-Schema-driven renderer

Every form in the system flows through `FormRenderer` here. See `docs/conventions/04-forms.md`.

## Files (Plan 2 fills these in)

- `FormRenderer.tsx` — recursive renderer reading JSON Schema
- `FieldRegistry.ts` — map `x-widget` → field component
- `fields/{String,Number,Boolean,Date,Enum,File,Array,Object}.tsx` — primitive fields
- `resolver.ts` — ajv resolver for RHF

## Rules

- All fields use `@/components/ui/*` primitives for rendering.
- Cross-field rules go through `@/lib/ajv.ts` (which registers FormRuleRegistry entries).
- Custom widgets extend via `FieldRegistry.register("x-widget", Component)`, not by patching FormRenderer.

## Anti-patterns

- Taking a `render` prop that lets consumers bypass the schema.
- Per-form custom validators (ajv only).
- Using `<input>` anywhere — always `@/components/ui/Input` (via a field component).
