import { forwardRef } from "react";
import type { FieldProps } from "./StringField";
import { StringField } from "./StringField";

export const DateField = forwardRef<HTMLInputElement, FieldProps>(function DateField(props, ref) {
  return <StringField {...props} ref={ref} />;
});
DateField.displayName = "DateField";
