import { useState, useEffect } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { MedicalButton, Sheet } from "@/components";
import { cn } from "@/lib/utils";
import { createReminder, updateReminder, getReminder } from "@/api/reminders";
import { useTelegram } from "@/hooks/useTelegram";
import { useToast } from "@/hooks/use-toast";
import {
  buildReminderPayload,
  type ScheduleKind,
  type ReminderFormValues,
  type ReminderType as ApiReminderType,
} from "@/features/reminders/api/buildPayload";
import { Reminder as ApiReminder } from "@sdk";

// Reminder type returned from API may contain legacy value "meds",
// normalize it to "medicine" for UI usage
type ReminderType = "sugar" | "insulin" | "meal" | "medicine" | "meds";
type NormalizedReminderType = "sugar" | "insulin" | "meal" | "medicine";

const normalizeType = (t: ReminderType): NormalizedReminderType =>
  t === "meds" ? "medicine" : t;

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

const mapType = (t: NormalizedReminderType): ApiReminderType => {
  switch (t) {
    case "sugar":
      return "sugar";
    case "insulin":
      return "insulin_short";
    case "meal":
      return "meal";
    default:
      return "custom";
  }
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

interface Reminder {
  id: number;
  type: NormalizedReminderType;
  title: string;
  time: string;
  interval?: number;
}

export default function CreateReminder() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const { user, sendData } = useTelegram();
  const { toast } = useToast();
  const [editing, setEditing] = useState<Reminder | undefined>(
    (location.state as Reminder | undefined) ?? undefined,
  );

  const [type, setType] = useState<NormalizedReminderType>(
    editing?.type ?? "sugar",
  );
  const [kind, setKind] = useState<ScheduleKind>("at_time");
  const [title, setTitle] = useState(editing?.title ?? "");
  const [time, setTime] = useState(editing?.time ?? "");
  const [interval, setInterval] = useState<number | undefined>(editing?.interval ?? 60);
  const [minutesAfter, setMinutesAfter] = useState<number | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [typeOpen, setTypeOpen] = useState(false);

  useEffect(() => {
    if (!editing && params.id && user?.id) {
      (async () => {
        try {
          const data = await getReminder(user.id, Number(params.id));
          if (data) {
            const nt = normalizeType(data.type as ReminderType);
            const loaded: Reminder = {
              id: data.id ?? Number(params.id),
              type: nt,
              title: data.title ?? TYPES[nt].label,
              time: data.time || "",
              interval: data.intervalHours != null ? data.intervalHours * 60 : undefined,
            };
            setEditing(loaded);
            setType(loaded.type);
            setTitle(loaded.title);
            setTime(loaded.time);
            setInterval(loaded.interval ?? 60);
            setKind(loaded.interval != null ? "every" : "at_time");
          } else {
            const message = "Не удалось загрузить напоминание";
            setError(message);
            toast({ title: "Ошибка", description: message, variant: "destructive" });
          }
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Не удалось загрузить напоминание";
          setError(message);
          toast({ title: "Ошибка", description: message, variant: "destructive" });
        }
      })();
    }
  }, [editing, params.id, user?.id, toast]);

  const validTime = kind !== "at_time" || isValidTime(time);
  const validInterval =
    kind !== "every" || (typeof interval === "number" && interval >= 5);
  const validMinutesAfter =
    kind !== "after_event" ||
    (typeof minutesAfter === "number" && minutesAfter >= 1);
  const formValid = validTime && validInterval && validMinutesAfter;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid || !user?.id) return;
    setError(null);
    const formValues: ReminderFormValues = {
      telegramId: user.id,
      type: mapType(type),
      kind,
      time,
      intervalMinutes: interval,
      minutesAfter,
      title,
      isEnabled: true,
    };
    const payload = {
      ...buildReminderPayload(formValues),
      ...(editing ? { id: editing.id } : {}),
    };
    try {
      const res = editing
        ? await updateReminder(payload as unknown as ApiReminder)
        : await createReminder(payload as unknown as ApiReminder);
      const rid = editing ? editing.id : res?.id;
      const value =
        kind === "at_time"
          ? time
          : kind === "every"
            ? `${interval}m`
            : `${minutesAfter}m`;
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

  const apiType = mapType(type);
  const preview = buildReminderPayload({
    telegramId: user?.id ?? 0,
    type: apiType,
    kind,
    time,
    intervalMinutes: interval,
    minutesAfter,
    title,
  });
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
      <div>
        <label htmlFor="kind">Тип расписания</label>
        <select
          id="kind"
          className="input"
          value={kind}
          onChange={(e) => {
            const nextKind = e.target.value as ScheduleKind;
            setKind(nextKind);
            setTime("");
            setInterval(undefined);
            setMinutesAfter(undefined);
          }}
        >
          <option value="at_time">По времени</option>
          <option value="every">Каждые N мин</option>
          <option value="after_event">После события</option>
        </select>
      </div>

      {kind === "at_time" && (
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
      )}
      {kind === "every" && (
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
              const value = e.target.value ? Number(e.target.value) : undefined;
              setInterval(value);
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
      )}
      {kind === "after_event" && (
        <div>
          <label htmlFor="minutesAfter">Через (мин)</label>
          <input
            id="minutesAfter"
            className="input"
            type="number"
            min={5}
            step={5}
            value={minutesAfter ?? ""}
            onChange={(e) => {
              const value = e.target.value ? Number(e.target.value) : undefined;
              setMinutesAfter(value);
            }}
          />
        </div>
      )}

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
            {preview.title}
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

