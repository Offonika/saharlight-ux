import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

interface DayOfWeekPickerProps {
  /** Selected days of week (1-7, where 1 is Monday) */
  value: number[];
  /** Callback invoked with new selection */
  onChange: (value: number[]) => void;
  /**
   * Localized names for days of week starting from Monday.
   * If not provided, the current locale will be used via `Intl.DateTimeFormat`.
   */
  dayNames?: string[];
}

const defaultDayNames = Array.from({ length: 7 }, (_, i) =>
  new Intl.DateTimeFormat(undefined, { weekday: "short" }).format(
    // Use fixed date starting from Monday 2024-01-01
    new Date(Date.UTC(2024, 0, i + 1))
  )
);

/**
 * Multi-select control for choosing days of the week.
 *
 * @example
 * ```tsx
 * const [days, setDays] = useState<number[]>([]);
 * <DayOfWeekPicker
 *   value={days}
 *   onChange={setDays}
 *   dayNames={["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]}
 * />
 * ```
 */
export function DayOfWeekPicker({ value, onChange, dayNames = defaultDayNames }: DayOfWeekPickerProps) {
  return (
    <ToggleGroup
      type="multiple"
      className="grid grid-cols-7 gap-1"
      value={value.map(String)}
      onValueChange={(vals) => onChange(vals.map((v) => parseInt(v, 10)))}
    >
      {dayNames.map((name, index) => (
        <ToggleGroupItem key={index} value={String(index + 1)} className="h-8">
          {name}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}

export default DayOfWeekPicker;

