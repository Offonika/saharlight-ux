import React from "react";
import { cn } from "@/lib/utils";

const PRESETS = [60, 90, 120, 150, 180, 240];

export interface AfterEventDelayProps {
  value: number | undefined;
  onChange: (value: number | undefined) => void;
  error?: string;
}

const AfterEventDelay: React.FC<AfterEventDelayProps> = ({
  value,
  onChange,
  error,
}) => {
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    const num = val === "" ? undefined : Number(val);
    onChange(Number.isNaN(num) ? undefined : num);
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-foreground">
          Задержка после еды (мин)
        </label>
        <p className="text-xs text-muted-foreground mt-1">
          Сработает после записи приёма пищи в «Истории»
        </p>
      </div>
      <input
        type="number"
        min={5}
        max={480}
        step={5}
        aria-label="Задержка после еды (мин)"
        className="medical-input"
        value={value ?? ""}
        onChange={handleInputChange}
      />
      {error && <p className="text-xs text-destructive mt-1">{error}</p>}
      <p className="text-xs text-muted-foreground">
        Рекомендации: 60–90 — промежуточная; 120 — основная; 180–240 — поздняя
      </p>
      <div className="flex gap-2 flex-wrap">
        {PRESETS.map((m) => (
          <button
            key={m}
            type="button"
            aria-pressed={value === m}
            onClick={() => onChange(m)}
            className={cn(
              "px-3 py-1 rounded-lg border transition-colors",
              value === m
                ? "bg-primary text-primary-foreground border-primary shadow-soft"
                : "border-border bg-background text-foreground hover:bg-secondary"
            )}
          >
            {m}
          </button>
        ))}
      </div>
    </div>
  );
};

export default AfterEventDelay;

