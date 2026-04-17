import { forwardRef } from "react";
import { Input } from "@/components/ui/input";
import type { FieldProps } from "./StringField";

export const DateField = forwardRef<HTMLInputElement, FieldProps>(function DateField(
  { name, schema, register, error },
  ref,
) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <Input id={name} type="date" ref={ref} {...register(name)} />
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
DateField.displayName = "DateField";
