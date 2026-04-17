import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { FieldProps } from "./StringField";

export function NumberField({ name, schema, register, error }: FieldProps) {
  const min = schema.minimum as number | undefined;
  const max = schema.maximum as number | undefined;
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={name}>{(schema.title as string) ?? name}</Label>
      <Input
        id={name}
        type="number"
        {...register(name, { valueAsNumber: true })}
        {...(min !== undefined ? { min } : {})}
        {...(max !== undefined ? { max } : {})}
      />
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
}
