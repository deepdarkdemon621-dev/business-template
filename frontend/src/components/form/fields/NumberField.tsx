import { forwardRef } from "react";
import type { FieldProps } from "./StringField";
import { StringField } from "./StringField";

export const NumberField = forwardRef<HTMLInputElement, FieldProps>(function NumberField(
  props,
  ref,
) {
  return <StringField {...props} ref={ref} />;
});
NumberField.displayName = "NumberField";
