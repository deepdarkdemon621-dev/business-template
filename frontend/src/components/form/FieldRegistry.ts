import type { ComponentType } from "react";
import { StringField, type FieldProps } from "./fields/StringField";
import { NumberField } from "./fields/NumberField";
import { BooleanField } from "./fields/BooleanField";
import { DateField } from "./fields/DateField";
import { EnumField } from "./fields/EnumField";

export type { FieldProps };
export type FieldComponent = ComponentType<FieldProps>;

const byType: Record<string, FieldComponent> = {
  string: StringField,
  number: NumberField,
  integer: NumberField,
  boolean: BooleanField,
};

const byWidget: Record<string, FieldComponent> = {
  date: DateField,
  enum: EnumField,
};

export function resolveFieldComponent(schema: Record<string, unknown>): FieldComponent {
  const widget = schema["x-widget"];
  if (typeof widget === "string" && byWidget[widget]) return byWidget[widget];
  if (Array.isArray(schema.enum)) return EnumField;

  const t = schema.type;
  if (typeof t === "string" && byType[t]) return byType[t];
  throw new Error(`Unsupported schema for field: ${JSON.stringify(schema)}`);
}
