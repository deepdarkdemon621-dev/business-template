// react-day-picker v9 — CSS import path differs from v8 (no `dist/` prefix in v9)
import { DayPicker, type DayPickerProps } from "react-day-picker";
import "react-day-picker/src/style.css";
import { cn } from "@/lib/utils";

export type CalendarProps = DayPickerProps;

export function Calendar({ className, ...props }: CalendarProps) {
  return <DayPicker className={cn("p-2", className)} {...props} />;
}
