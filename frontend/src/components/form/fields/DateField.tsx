import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { FieldProps } from "./StringField";

export function DateField({ name, schema, register, error }: FieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={name}>{(schema.title as string) ?? name}</Label>
      <Input id={name} type="date" {...register(name)} />
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
}
