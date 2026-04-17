import { forwardRef } from "react";
import type { FieldProps } from "./StringField";

export const EnumField = forwardRef<HTMLSelectElement, FieldProps>(function EnumField(
  { name, schema, register, error },
  ref,
) {
  const values = (schema.enum as string[] | undefined) ?? [];
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <select
        id={name}
        aria-label={(schema.title as string) ?? name}
        ref={ref}
        {...register(name)}
        className="h-9 rounded-md border border-input bg-background px-3 text-sm"
      >
        {values.map((v) => (
          <option key={v} value={v}>
            {v}
          </option>
        ))}
      </select>
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
EnumField.displayName = "EnumField";
