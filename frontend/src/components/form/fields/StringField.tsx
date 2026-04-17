import type { UseFormRegister } from "react-hook-form";
import { Input } from "@/components/ui/input";

export interface FieldProps {
  name: string;
  schema: Record<string, unknown>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- schema-driven: field names are runtime strings, not static Path<T>
  register: UseFormRegister<any>;
  error?: string;
}

export function StringField({ name, schema, register, error }: FieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <Input id={name} {...register(name)} />
      {error && (
        <span role="alert" className="text-sm text-red-600">
          {error}
        </span>
      )}
    </div>
  );
}
