# 04 · Forms (RHF + ajv + JSON Schema)

## Rule

> **One form pipeline for the entire app: JSON Schema → RHF `useForm` with ajv resolver → `<FormRenderer>` → submit.**

## Why

Any deviation fragments the validation story (01-schema-validation) and the UI layer (03-ui-primitives). One pipeline = AI has one pattern to follow = no drift.

## Pipeline

```
API endpoint (FastAPI) ──▶ OpenAPI / JSON Schema
                                     │
                        static schema │ or   dynamic schema (form engine, V2)
                                     ▼
                        fetch() as JSON Schema
                                     │
                                     ▼
             useForm({ resolver: ajvResolver(schema, { customRules }) })
                                     │
                                     ▼
                          <FormRenderer schema={schema} />
                                     │
                                     ▼
                      recurse into Field components
                           (fields live in @/components/form/fields/)
                                     │
                                     ▼
                                 handleSubmit
```

## Components

- `@/components/form/FormRenderer.tsx` — recursive renderer reading JSON Schema and `x-rules`
- `@/components/form/fields/String.tsx` / `Number.tsx` / `Boolean.tsx` / `Date.tsx` / `Enum.tsx` / `File.tsx` / `Array.tsx` / `Object.tsx` — one per JSON Schema type
- `FieldRegistry` — maps `x-widget` hints to custom fields (e.g. `x-widget: "rich-text"` → rich text editor)
- `@/lib/ajv.ts` — singleton ajv instance with `ajv-formats` + all FormRuleRegistry rules registered

## Do

- Build all forms via `<FormRenderer schema={...} />`.
- Extend by registering new field widgets in `FieldRegistry`.
- Include cross-field rules via `json_schema_extra={"x-rules": [...]}` on the Pydantic model (see 01).

## Don't

- Hand-write `<input>`, `<Input>`, `<TextField>` inside a business page.
- Replace ajv with Zod, Yup, or custom validators.
- Inline `@model_validator` cross-field rules that bypass FormRuleRegistry.

## Mechanical enforcement

- `scripts/audit/audit_forms_fe.ts` (Plan 2) — scans `src/modules/**/*.tsx` for direct `<Input|<TextField|<Field` usages outside `@/components/form/`
- contract test: every x-rule type seen in generated OpenAPI must be registered in `@/lib/ajv.ts`

## Concrete renderer (shipped in Plan 2)

```tsx
import { FormRenderer } from "@/components/form/FormRenderer";
import { client } from "@/api/client";
import { isProblemDetails } from "@/lib/problem-details";

const schema = {
  type: "object",
  properties: {
    newPassword: { type: "string", title: "New password" },
    confirm: { type: "string", title: "Confirm" },
  },
  required: ["newPassword", "confirm"],
  mustMatch: { a: "newPassword", b: "confirm" },
};

export function PasswordResetForm() {
  return (
    <FormRenderer
      schema={schema}
      onSubmit={async (values, { setFieldErrors }) => {
        try {
          await client.post("/password-reset", values);
        } catch (err) {
          if (isProblemDetails(err) && err.errors) {
            setFieldErrors(Object.fromEntries(err.errors.map((e) => [e.field, e.message ?? e.code])));
          }
        }
      }}
    >
      <button type="submit">Save</button>
    </FormRenderer>
  );
}
```

- Every form in `modules/` uses `<FormRenderer>`. No hand-rolled `<input>` trees.
- `x-rules` in the schema (emitted automatically by backend `__rules__`) are enforced by the shared Ajv singleton.
- Server-side `FieldError`s from a `ProblemDetails` response are surfaced inline via `setFieldErrors`.
