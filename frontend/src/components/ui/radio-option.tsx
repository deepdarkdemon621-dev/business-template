import { forwardRef, type InputHTMLAttributes } from "react";

export type RadioOptionProps = InputHTMLAttributes<HTMLInputElement>;

export const RadioOption = forwardRef<HTMLInputElement, RadioOptionProps>(
  function RadioOption(props, ref) {
    return <input ref={ref} type="radio" {...props} />;
  },
);
