import type { UseFormRegister } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface FieldProps {
  name: string;
  schema: Record<string, unknown>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- schema-driven: field names are runtime strings, not static Path<T>
  register: UseFormRegister<any>;
  error?: string;
}

export function StringField({ name, schema, register, error }: FieldProps) {
  const inputType = (schema["x-inputType"] as string | undefined) ?? "text";
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={name}>{(schema.title as string) ?? name}</Label>
      <Input id={name} type={inputType} {...register(name)} />
      {error && (
        <span role="alert" className="text-sm text-red-600">
          {error}
        </span>
      )}
    </div>
  );
}
