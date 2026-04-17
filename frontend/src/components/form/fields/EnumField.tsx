import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { FieldProps } from "./StringField";

export function EnumField({ name, schema, register, error }: FieldProps) {
  const values = (schema.enum as string[] | undefined) ?? [];
  const { onChange, onBlur, ref } = register(name);
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={name}>{(schema.title as string) ?? name}</Label>
      <Select
        name={name}
        onValueChange={(v) => onChange({ target: { name, value: v } })}
      >
        <SelectTrigger id={name} ref={ref} onBlur={onBlur}>
          <SelectValue placeholder="Select..." />
        </SelectTrigger>
        <SelectContent>
          {values.map((v) => (
            <SelectItem key={v} value={v}>
              {v}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
}
