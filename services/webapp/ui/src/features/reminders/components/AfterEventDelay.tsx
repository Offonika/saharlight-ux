import React from "react";

interface Props {
  value?: number;
  onChange: (v?: number) => void;
  error?: string;
}

const PRESETS = [60, 90, 120, 150, 180, 240];

export default function AfterEventDelay({ value, onChange, error }: Props) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value === "" ? undefined : Number(e.target.value);
    onChange(val);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <label className="block text-sm font-medium text-foreground">
          Задержка после еды (мин)
        </label>
        <span className="text-xs text-muted-foreground">
          Сработает после записи приёма пищи в «Истории»
        </span>
      </div>
      <input
        type="number"
        min={5}
        max={480}
        step={5}
        aria-label="Задержка после еды (мин)"
        className={`medical-input rounded-xl ${error ? "border-destructive focus:border-destructive" : ""}`}
        value={value ?? ""}
        onChange={handleChange}
      />
      {error && (
        <p className="text-xs text-destructive mt-1">{error}</p>
      )}
      <div className="flex gap-2 flex-wrap">
        {PRESETS.map((m) => (
          <button
            key={m}
            type="button"
            aria-pressed={value === m}
            onClick={() => onChange(m)}
            className={`px-3 py-2 rounded-xl border text-sm font-medium transition-all duration-200 ${
              value === m
                ? "bg-primary text-primary-foreground border-primary shadow-soft"
                : "border-border bg-background text-foreground hover:bg-secondary hover:border-primary/20"
            }`}
          >
            {m}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Рекомендации: 60–90 — промежуточная; 120 — основная; 180–240 — поздняя
      </p>
    </div>
  );
}

