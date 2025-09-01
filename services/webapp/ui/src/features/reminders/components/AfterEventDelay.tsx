import React from "react";

interface AfterEventDelayProps {
  value?: number;
  onChange: (v?: number) => void;
  error?: string;
}

export default function AfterEventDelay({
  value,
  onChange,
  error,
}: AfterEventDelayProps) {
  const presets = [60, 90, 120, 150, 180, 240];
  const activePreset = presets.includes(value ?? 0) ? value : undefined;

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value);
    onChange(Number.isNaN(v) ? undefined : v);
  };

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-foreground">
        <span className="flex items-center gap-2">
          <span>Задержка после еды (мин)</span>
          <span className="text-xs text-muted-foreground">
            Сработает после записи приёма пищи в «Истории»
          </span>
        </span>
      </label>
      <input
        type="number"
        min={5}
        max={480}
        step={5}
        aria-label="Задержка после еды (мин)"
        className={`medical-input ${
          error ? "border-destructive focus:border-destructive" : ""
        }`}
        value={value ?? ""}
        onChange={handleInput}
      />
      {error && (
        <p className="text-xs text-destructive mt-1">{error}</p>
      )}
        <p className="text-xs text-muted-foreground">
          Рекомендации: 60–90 — промежуточная; 120 — основная;
          180–240 — поздняя
        </p>
      <div className="flex gap-2 flex-wrap">
        {presets.map((m) => {
          const active = activePreset === m;
          return (
            <button
              key={m}
              type="button"
              aria-pressed={active}
              onClick={() => onChange(m)}
                className={`px-3 py-1 rounded-lg border text-sm font-medium
                transition-all duration-200 ${
                  active
                    ? "bg-primary text-primary-foreground border-primary shadow-soft"
                    : "border-border bg-background text-foreground " +
                      "hover:bg-secondary " +
                      "hover:border-primary/20"
                }`}
            >
              {m} мин
            </button>
          );
        })}
      </div>
    </div>
  );
}

