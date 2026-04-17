import { forwardRef } from "react";
import { Input } from "@/components/ui/input";

export interface FieldProps {
  name: string;
  schema: Record<string, unknown>;
  register: any;
  error?: string;
}

export const StringField = forwardRef<HTMLInputElement, FieldProps>(function StringField(
  { name, schema, register, error },
  ref,
) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <Input id={name} ref={ref} {...register(name)} />
      {error && (
        <span role="alert" className="text-sm text-red-600">
          {error}
        </span>
      )}
    </div>
  );
});
StringField.displayName = "StringField";
