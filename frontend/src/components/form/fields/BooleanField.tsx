import { forwardRef } from "react";
import type { FieldProps } from "./StringField";
import { StringField } from "./StringField";

export const BooleanField = forwardRef<HTMLInputElement, FieldProps>(function BooleanField(
  props,
  ref,
) {
  return <StringField {...props} ref={ref} />;
});
BooleanField.displayName = "BooleanField";
