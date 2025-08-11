import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MedicalButton, Sheet } from "@/components";
import { cn } from "@/lib/utils";

type ReminderType = "sugar" | "insulin" | "meal";

const TYPES: Record<ReminderType, { label: string; emoji: string }> = {
  sugar: { label: "Сахар", emoji: "🩸" },
  insulin: { label: "Инсулин", emoji: "💉" },
  meal: { label: "Приём пищи", emoji: "🍽️" }
};

const PRESETS: Record<ReminderType, number[]> = {
  sugar: [15, 30, 60],
  insulin: [120, 180, 240],
  meal: [180, 240, 360]
};

function isValidTime(time: string): boolean {
  const [hours, minutes] = time.split(":").map(Number);
  return (
    Number.isInteger(hours) &&
    Number.isInteger(minutes) &&
    hours >= 0 &&
    hours <= 23 &&
    minutes >= 0 &&
    minutes <= 59
  );
}

export default function CreateReminder() {
  const navigate = useNavigate();

  const [type, setType] = useState<ReminderType>("sugar");
  const [title, setTitle] = useState("");
  const [time, setTime] = useState("");
  const [interval, setInterval] = useState<number | undefined>(60);
  const [error, setError] = useState<string | null>(null);
  const [typeOpen, setTypeOpen] = useState(false);

  const validName = title.trim().length >= 2;
  const validTime = isValidTime(time);
  const validInterval = typeof interval === "number" && interval >= 5;
  const formValid = validName && validTime && validInterval;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid) return;
    setError(null);
    try {
      const res = await fetch("/reminders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type,
          text: title.trim(),
          value: `${time}|${interval}`
        })
      });
      if (!res.ok) {
        throw new Error("Failed to create reminder");
      }
      navigate("/reminders");
    } catch {
      setError("Не удалось сохранить напоминание");
    }
  };

  const typeInfo = TYPES[type];

  return (
    <form onSubmit={handleSubmit} className="pb-24 space-y-4">
      {error && <div className="mb-4 text-destructive">{error}</div>}

      <div>
        <label className="block mb-1">Тип</label>
        <button
          type="button"
          className="flex items-center gap-2 px-3 py-1.5 rounded-full border bg-secondary text-sm"
          onClick={() => setTypeOpen(true)}
        >
          <span>{typeInfo.emoji}</span>
          <span>{typeInfo.label}</span>
        </button>
      </div>

      <div>
        <label htmlFor="title">Название</label>
        <input
          id="title"
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={40}
        />
      </div>

      <div className="grid gap-2 md:grid-cols-2">
        <div>
          <label htmlFor="time">Время</label>
          <input
            id="time"
            className="input"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="interval">Интервал (мин)</label>
          <input
            id="interval"
            className="input"
            type="number"
            min={5}
            step={5}
            value={interval ?? ""}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              setInterval(Number.isNaN(val) ? undefined : val);
            }}
          />
          <div className="flex flex-wrap gap-2 mt-2">
            {PRESETS[type].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setInterval(n)}
                className={cn(
                  "px-3 py-1 rounded-full border text-sm",
                  interval === n &&
                    "bg-primary text-primary-foreground border-primary"
                )}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
      </div>

      <Sheet open={typeOpen} onClose={() => setTypeOpen(false)}>
        <div className="p-4 grid grid-cols-3 gap-4">
          {(Object.keys(TYPES) as ReminderType[]).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => {
                setType(key);
                setTypeOpen(false);
              }}
              className="flex flex-col items-center justify-center p-4 rounded-lg border"
            >
              <span className="text-2xl">{TYPES[key].emoji}</span>
              <span className="mt-2 text-sm">{TYPES[key].label}</span>
            </button>
          ))}
        </div>
      </Sheet>

      <div className="fixed bottom-0 left-0 right-0 border-t bg-background p-4 flex items-center justify-between gap-4">
        <div className="text-sm">
          <span>{typeInfo.emoji} </span>
          {title.trim() || typeInfo.label}, {time}
          {interval && ` • каждые ${interval} мин`}
        </div>
        <div className="flex gap-2">
          <MedicalButton
            type="button"
            variant="secondary"
            onClick={() => navigate("/reminders")}
          >
            Отмена
          </MedicalButton>
          <MedicalButton type="submit" disabled={!formValid}>
            Сохранить
          </MedicalButton>
        </div>
      </div>
    </form>
  );
}

