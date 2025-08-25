import { cn } from "@/lib/utils";
import { useCallback } from "react";

export interface DayOfWeekPickerProps {
  value?: number[];
  onChange: (next: number[]) => void;
  shortNames: string[];
  longNames: string[];
}

export default function DayOfWeekPicker({
  value = [],
  onChange,
  shortNames,
  longNames,
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
      {shortNames.map((day, index) => {
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
            aria-label={longNames[index]}
          >
            {day}
          </button>
        );
      })}
    </div>
  );
}

