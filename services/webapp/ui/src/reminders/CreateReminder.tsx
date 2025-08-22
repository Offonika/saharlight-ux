import { useState, useEffect } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { MedicalButton, Sheet } from "@/components";
import { cn } from "@/lib/utils";
import { createReminder, updateReminder, getReminder } from "@/api/reminders";
import { Reminder as ApiReminder } from "@offonika/diabetes-ts-sdk";
import { useTelegramContext } from "@/contexts/telegram-context";
import { useToast } from "@/hooks/use-toast";
import {
  normalizeReminderType,
  type NormalizedReminderType,
} from "@/lib/reminders";
import { isValidTime } from "@/lib/time";
import type { Reminder } from "@/types/reminder";

const TYPES: Record<NormalizedReminderType, { label: string; emoji: string }> = {
  sugar: { label: "Сахар", emoji: "🩸" },
  insulin: { label: "Инсулин", emoji: "💉" },
  meal: { label: "Приём пищи", emoji: "🍽️" },
  medicine: { label: "Лекарства", emoji: "💊" }
};

const PRESETS: Record<NormalizedReminderType, number[]> = {
  sugar: [15, 30, 60],
  insulin: [120, 180, 240],
  meal: [180, 240, 360],
  medicine: [240, 480, 720]
};


export default function CreateReminder() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const { user, sendData } = useTelegramContext();
  const { toast } = useToast();
  const [editing, setEditing] = useState<Reminder | undefined>(
    (location.state as Reminder | undefined) ?? undefined,
  );

  const [type, setType] = useState<NormalizedReminderType>(
    editing?.type ?? "sugar",
  );
  const [title, setTitle] = useState(editing?.title ?? "");
  const [time, setTime] = useState(editing?.time ?? "");
  // interval is stored in minutes for UI, API expects hours
  const [intervalMinutes, setIntervalMinutes] =
    useState<number | undefined>(editing?.interval);
  const [error, setError] = useState<string | null>(null);
  const [typeOpen, setTypeOpen] = useState(false);

  useEffect(() => {
    if (!params.id || !user?.id) return;
    const controller = new AbortController();
    const id = Number(params.id);
    if (Number.isNaN(id)) {
      const message = "Некорректный ID напоминания";
      setError(message);
      toast({ title: "Ошибка", description: message, variant: "destructive" });
      return () => controller.abort();
    }
    (async () => {
      try {
        const data = await getReminder(user.id, id, controller.signal);
        if (data) {
          const nt = normalizeReminderType(data.type);
          const loaded: Reminder = {
            id: data.id ?? id,
            type: nt,
            title: data.title ?? TYPES[nt].label,
            time: data.time || "",
            interval: data.intervalHours != null ? data.intervalHours * 60 : undefined,
          };
          setEditing(loaded);
          setType(loaded.type);
          setTitle(loaded.title);
          setTime(loaded.time);
          setIntervalMinutes(loaded.interval);
        } else {
          const message = "Не удалось загрузить напоминание";
          setError(message);
          toast({ title: "Ошибка", description: message, variant: "destructive" });
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        const message =
          err instanceof Error ? err.message : "Не удалось загрузить напоминание";
        setError(message);
        toast({ title: "Ошибка", description: message, variant: "destructive" });
      }
    })();
    return () => {
      controller.abort();
    };
  }, [params.id, user?.id, toast]);

  const validName = title.trim().length >= 2;
  const validTime = isValidTime(time);
  const validInterval = editing
    ? intervalMinutes == null || intervalMinutes >= 5
    : typeof intervalMinutes === "number" && intervalMinutes >= 5;
  const formValid = validName && validTime && validInterval;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid || !user?.id) return;
    setError(null);
    const payload: ApiReminder = {
      telegramId: user.id,
      type,
      time,
      intervalHours:
        intervalMinutes != null ? intervalMinutes / 60 : undefined,
      isEnabled: true,
      ...(editing ? { id: editing.id } : {}),
    };
    try {
      const res = editing
        ? await updateReminder(payload)
        : await createReminder(payload);
      const rid = editing ? editing.id : res?.id;
      const hours =
        intervalMinutes != null ? intervalMinutes / 60 : undefined;
      const value =
        hours != null && Number.isInteger(hours) ? `${hours}h` : time;
      if (rid) {
        sendData({ id: rid, type, value });
      }
      navigate("/reminders");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Не удалось сохранить напоминание";
      setError(message);
      toast({ title: "Ошибка", description: message, variant: "destructive" });
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
            value={intervalMinutes ?? ""}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              setIntervalMinutes(Number.isNaN(val) ? undefined : val);
            }}
          />
          <div className="flex flex-wrap gap-2 mt-2">
            {PRESETS[type].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setIntervalMinutes(n)}
                className={cn(
                  "px-3 py-1 rounded-full border text-sm",
                  intervalMinutes === n &&
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
          {(Object.keys(TYPES) as NormalizedReminderType[]).map((key) => (
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
          {intervalMinutes && ` • каждые ${intervalMinutes} мин`}
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

