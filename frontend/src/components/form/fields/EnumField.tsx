import { forwardRef } from "react";
import type { FieldProps } from "./StringField";
import { StringField } from "./StringField";

export const EnumField = forwardRef<HTMLInputElement, FieldProps>(function EnumField(props, ref) {
  return <StringField {...props} ref={ref} />;
});
EnumField.displayName = "EnumField";
