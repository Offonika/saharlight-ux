import { cn } from "@/lib/utils";
import { useCallback } from "react";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const WEEKDAY_LABELS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export interface DayOfWeekPickerProps {
  value?: number[];
  onChange: (next: number[]) => void;
}

export default function DayOfWeekPicker({
  value = [],
  onChange,
}: DayOfWeekPickerProps) {
  const toggle = useCallback(
    (index: number) => {
      const next = value.includes(index)
        ? value.filter((d) => d !== index)
        : [...value, index];
      onChange(next);
    },
    [value, onChange],
  );

  return (
    <div className="flex gap-2">
      {WEEKDAYS.map((day, index) => {
        const active = value.includes(index);
        return (
          <button
            key={day}
            type="button"
            onClick={() => toggle(index)}
            className={cn(
              "w-8 h-8 rounded-full border text-sm",
              active && "bg-primary text-primary-foreground border-primary",
            )}
            aria-pressed={active}
            aria-label={WEEKDAY_LABELS[index]}
          >
            {day[0]}
          </button>
        );
      })}
    </div>
  );
}

