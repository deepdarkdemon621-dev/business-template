import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { FieldProps } from "./StringField";

export function BooleanField({ name, schema, register, error }: FieldProps) {
  const { onChange, ref, ...rest } = register(name);
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
      <Label htmlFor={name}>{(schema.title as string) ?? name}</Label>
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
}
