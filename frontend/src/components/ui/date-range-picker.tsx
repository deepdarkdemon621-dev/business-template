import { format } from "date-fns";
import type { DateRange } from "react-day-picker";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

// DateRangeValue mirrors react-day-picker's DateRange but with optional `from`
// so consumers can start with an empty state.
export type DateRangeValue = { from?: Date; to?: Date };

export function DateRangePicker({
  value,
  onChange,
  placeholder = "Select range",
}: {
  value: DateRangeValue;
  onChange: (v: DateRangeValue) => void;
  placeholder?: string;
}) {
  const label =
    value.from && value.to
      ? `${format(value.from, "yyyy-MM-dd")} → ${format(value.to, "yyyy-MM-dd")}`
      : value.from
        ? `${format(value.from, "yyyy-MM-dd")} →`
        : placeholder;

  // react-day-picker v9 DateRange requires `from: Date | undefined`
  const selected: DateRange = { from: value.from, to: value.to };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          {label}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0">
        <Calendar
          mode="range"
          selected={selected}
          onSelect={(r) => onChange({ from: r?.from, to: r?.to })}
          numberOfMonths={2}
        />
        <div className="flex justify-end gap-2 p-2 border-t">
          <Button variant="ghost" size="sm" onClick={() => onChange({})}>
            Clear
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
