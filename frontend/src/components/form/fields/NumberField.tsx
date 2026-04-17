import { forwardRef } from "react";
import { Input } from "@/components/ui/input";
import type { FieldProps } from "./StringField";

export const NumberField = forwardRef<HTMLInputElement, FieldProps>(function NumberField(
  { name, schema, register, error },
  ref,
) {
  const min = schema.minimum as number | undefined;
  const max = schema.maximum as number | undefined;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <Input
        id={name}
        type="number"
        ref={ref}
        {...register(name, { valueAsNumber: true })}
        {...(min !== undefined ? { min } : {})}
        {...(max !== undefined ? { max } : {})}
      />
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
NumberField.displayName = "NumberField";
