import { forwardRef } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import type { FieldProps } from "./StringField";

export const BooleanField = forwardRef<HTMLButtonElement, FieldProps>(function BooleanField(
  { name, schema, register, error },
  ref,
) {
  const { onChange, ...rest } = register(name);
  return (
    <div className="flex items-center gap-2">
      <Checkbox
        id={name}
        ref={ref}
        {...rest}
        onCheckedChange={(checked: boolean) =>
          onChange({ target: { name, value: checked } })
        }
      />
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
BooleanField.displayName = "BooleanField";
