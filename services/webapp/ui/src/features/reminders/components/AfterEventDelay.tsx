import React from "react";

interface Props {
  value?: number;
  onChange: (minutes: number) => void;
  presets?: number[];
}

const DEFAULT_PRESETS = [60, 90, 120];

export default function AfterEventDelay({
  value,
  onChange,
  presets = DEFAULT_PRESETS,
}: Props) {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-foreground">
        Задержка после события (мин)
      </label>
      <input
        type="number"
        min={1}
        className="medical-input"
        value={value ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="flex gap-2 flex-wrap">
        {presets.map((m) => (
          <button
            key={m}
            type="button"
            aria-pressed={value === m}
            className={`px-3 py-1 rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-colors ${
              value === m ? "bg-secondary" : ""
            }`}
            onClick={() => onChange(m)}
          >
            {m} мин
          </button>
        ))}
      </div>
    </div>
  );
}
