import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

const DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export interface DayOfWeekPickerProps {
  value?: number[];
  onChange(next: number[]): void;
}

export function DayOfWeekPicker({ value = [], onChange }: DayOfWeekPickerProps) {
  return (
    <ToggleGroup
      type="multiple"
      value={value.map(String)}
      onValueChange={(vals) => onChange(vals.map(Number))}
      className="justify-start"
    >
      {DAYS.map((label, idx) => (
        <ToggleGroupItem
          key={idx}
          value={String(idx + 1)}
          className="w-8 h-8"
          aria-label={label}
        >
          {label}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}

export default DayOfWeekPicker;
