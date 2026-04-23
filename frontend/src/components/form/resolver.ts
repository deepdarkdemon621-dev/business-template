import { toNestErrors } from "@hookform/resolvers";
import type { FieldError, FieldErrors, ResolverOptions, ResolverResult } from "react-hook-form";
import { ajv } from "@/lib/ajv";

/**
 * Build a react-hook-form resolver from a JSON Schema object,
 * validated through the shared Ajv singleton (which has mustMatch,
 * dateOrder, and ajv-formats already registered).
 *
 * We intentionally skip `@hookform/resolvers/ajv` because that
 * package creates its own `new Ajv()` on every call and therefore
 * loses our custom keywords.
 */

/** Remove `undefined` values and coerce DOM-native types to match the
 *  JSON Schema expectations.
 *
 *  RHF registers every field eagerly, so unset controls appear as
 *  `{ field: undefined }`.  Checkboxes default to the string `"on"`.
 *  Both cause spurious ajv type errors.  This function:
 *
 *  - Strips `undefined` keys (ajv would fail them on any non-string type)
 *  - Coerces `"on"` → `true` for boolean-typed properties
 *  - Coerces `""` → `undefined` (then stripped) for non-string types
 */
function prepareValues(
  raw: Record<string, unknown>,
  schema: Record<string, unknown>,
): Record<string, unknown> {
  const properties = (schema.properties ?? {}) as Record<string, Record<string, unknown>>;
  const out: Record<string, unknown> = {};

  for (const [k, v] of Object.entries(raw)) {
    const fieldSchema = properties[k];
    const schemaType = fieldSchema?.type;

    if (v === undefined) continue;

    // HTML checkbox default value from register()
    if (schemaType === "boolean") {
      if (v === "on" || v === true) {
        out[k] = true;
      } else if (v === "" || v === "off" || v === false) {
        out[k] = false;
      } else {
        out[k] = v;
      }
      continue;
    }

    // Empty string for non-string types → omit (treat as absent)
    if (v === "" && schemaType !== "string") continue;

    out[k] = v;
  }

  return out;
}

export function makeResolver(schema: object) {
  const validate = ajv.compile(schema);

  return (
    values: Record<string, unknown>,
    _context: unknown,
    options: ResolverOptions<Record<string, unknown>>,
  ): ResolverResult<Record<string, unknown>> => {
    const cleaned = prepareValues(values, schema as Record<string, unknown>);
    // ajv mutates `validate.errors` — safe to read synchronously.
    const valid = validate(cleaned);

    if (valid) return { values: cleaned, errors: {} };

    const fieldErrors: Record<string, FieldError> = {};

    for (const err of validate.errors ?? []) {
      // `required` errors report on the parent; shift to the missing child.
      let path = err.instancePath.substring(1).replace(/\//g, ".");
      if (err.keyword === "required" && err.params?.["missingProperty"]) {
        path = path ? `${path}.${err.params["missingProperty"]}` : (err.params["missingProperty"] as string);
      }

      // Custom rule keywords (mustMatch, dateOrder, passwordPolicy) emit on
      // the root object with no instancePath. Assign to the most relevant
      // field so the error shows up somewhere visible.
      if (!path && err.params) {
        const p = err.params as Record<string, unknown>;
        // mustMatch → b field; dateOrder → end field; passwordPolicy → field
        path =
          (p["b"] as string) ??
          (p["end"] as string) ??
          (p["field"] as string) ??
          "root";
      }

      if (!fieldErrors[path]) {
        fieldErrors[path] = { message: err.message ?? "invalid", type: err.keyword };
      }
    }

    return {
      values: {},
      errors: toNestErrors(fieldErrors as FieldErrors, options),
    };
  };
}
