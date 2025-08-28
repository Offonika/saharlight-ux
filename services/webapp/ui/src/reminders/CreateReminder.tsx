import { useState, useEffect } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { MedicalButton, Sheet } from "@/components";
import { MedicalHeader } from "@/components/MedicalHeader";
import { cn } from "@/lib/utils";
import { mockApi } from "@/api/mock-server";
import { useRemindersApi } from "@/features/reminders/api/reminders";
import type { ReminderSchema as ApiReminder } from "@sdk";
import { useTelegram } from "@/hooks/useTelegram";
import { validate, hasErrors } from "@/features/reminders/logic/validate";
import { useToast } from "@/shared/toast";

// Reminder type returned from API may contain legacy value "meds",
// normalize it to "medicine" for UI usage
type ReminderType = "sugar" | "insulin" | "meal" | "medicine" | "meds";
type NormalizedReminderType = "sugar" | "insulin" | "meal" | "medicine";

const normalizeType = (t: ReminderType): NormalizedReminderType =>
  t === "meds" ? "medicine" : t;

const TYPES: Record<NormalizedReminderType, { label: string; emoji: string }> = {
  sugar: { label: "Измерение сахара", emoji: "🩸" },
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
  const toast = useToast();
  const api = useRemindersApi();
  const [editing, setEditing] = useState<Reminder | undefined>(
    (location.state as Reminder | undefined) ?? undefined,
  );

  const [type, setType] = useState<NormalizedReminderType>(
    editing?.type ?? "sugar",
  );
  const [title, setTitle] = useState(editing?.title ?? "");
  const [time, setTime] = useState(editing?.time ?? "");
  // interval is stored in minutes for both UI and API (intervalHours is legacy)
  const [interval, setInterval] = useState<number | undefined>(editing?.interval ?? 60);
  const [error, setError] = useState<string | null>(null);
  const [typeOpen, setTypeOpen] = useState(false);

  // Form validation
  const formData = { kind: "at_time", time, intervalMinutes: interval };
  const errors = validate(formData as any);
  const formHasErrors = hasErrors(errors);

  useEffect(() => {
    if (!editing && params.id && user?.id) {
      (async () => {
        try {
          let data: ApiReminder | null = null;
          try {
            data = await api.remindersIdGet({ telegramId: user.id, id: Number(params.id) });
          } catch (apiError) {
            console.warn("Backend API failed, using mock API:", apiError);
            data = await mockApi.getReminder(user.id, Number(params.id));
          }
          if (data) {
            const nt = normalizeType(data.type as ReminderType);
            const loaded: Reminder = {
              id: data.id ?? Number(params.id),
              type: nt,
              title: data.title ?? TYPES[nt].label,
              time: data.time || "",
              interval:
                data.intervalMinutes != null
                  ? data.intervalMinutes
                  : data.intervalHours != null
                  ? data.intervalHours * 60
                  : undefined,
            };
            setEditing(loaded);
            setType(loaded.type);
            setTitle(loaded.title);
            setTime(loaded.time);
            setInterval(loaded.interval ?? 60);
          } else {
            const message = "Не удалось загрузить напоминание";
            setError(message);
            toast.error(message);
          }
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Не удалось загрузить напоминание";
          setError(message);
          toast.error(message);
        }
      })();
    }
  }, [editing, params.id, user?.id, toast, api]);

  const validName = title.trim().length >= 2;
  const validTime = isValidTime(time);
  const validInterval = typeof interval === "number" && interval >= 5;
  const formValid = validName && validTime && validInterval && !formHasErrors;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid || !user?.id) return;
    setError(null);
    const kind = interval != null ? "every" : "at_time";
    const payload: ApiReminder = {
      telegramId: user.id,
      type,
      kind,
      ...(kind === "at_time" ? { time } : { intervalMinutes: interval ?? undefined }),
      isEnabled: true,
      ...(editing ? { id: editing.id } : {}),
    };
    try {
      let res: { id?: number } | void;
      if (editing) {
        try {
          await api.remindersPatch({ reminder: payload });
          res = { id: editing.id };
        } catch (apiError) {
          console.warn("Backend API failed, using mock API:", apiError);
          await mockApi.updateReminder(payload);
          res = { id: editing.id };
        }
      } else {
        try {
          res = await api.remindersPost({ reminder: payload });
        } catch (apiError) {
          console.warn("Backend API failed, using mock API:", apiError);
          res = await mockApi.createReminder(payload);
        }
      }
      const rid = editing ? editing.id : res?.id;
      const hours = interval != null ? interval / 60 : undefined;
      const value =
        hours != null && Number.isInteger(hours) ? `${hours}h` : time;
      if (rid) {
        sendData({ id: rid, type, value });
      }
      toast.success(
        editing ? "Напоминание обновлено" : "Напоминание создано"
      );
      navigate("/reminders");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Не удалось сохранить напоминание";
      setError(message);
      toast.error(message);
    }
  };

  const typeInfo = TYPES[type];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <MedicalHeader 
        title={editing ? "Редактировать напоминание" : "Создать напоминание"}
        showBack 
        onBack={() => navigate("/reminders")}
      />
      
      <main className="container mx-auto px-4 py-6 pb-24">
        <form onSubmit={handleSubmit} className="max-w-xl mx-auto space-y-6 medical-card animate-slide-up">
          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
              {error}
            </div>
          )}

          {/* Тип напоминания */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Тип напоминания</label>
            <button
              type="button"
              className="flex items-center gap-3 px-4 py-3 rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-colors w-full justify-start"
              onClick={() => setTypeOpen(true)}
            >
              <span className="text-2xl">{typeInfo.emoji}</span>
              <span className="font-medium">{typeInfo.label}</span>
            </button>
          </div>

          {/* Название */}
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-foreground mb-2">
              Название напоминания
            </label>
            <input
              id="title"
              className="medical-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={40}
              placeholder={`Например: ${typeInfo.label} утром`}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Минимум 2 символа
            </p>
          </div>

          {/* Время и интервал */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="time" className="block text-sm font-medium text-foreground mb-2">
                Время
              </label>
              <input
                id="time"
                className={`medical-input ${errors.time ? "border-destructive focus:border-destructive" : ""}`}
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
              />
              {errors.time && (
                <p className="text-xs text-destructive mt-1">{errors.time}</p>
              )}
            </div>
            <div>
              <label htmlFor="interval" className="block text-sm font-medium text-foreground mb-2">
                Интервал (мин)
              </label>
              <input
                id="interval"
                className={`medical-input ${errors.intervalMinutes ? "border-destructive focus:border-destructive" : ""}`}
                type="number"
                min={5}
                step={5}
                value={interval ?? ""}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  setInterval(Number.isNaN(val) ? undefined : val);
                }}
                placeholder="60"
              />
              {errors.intervalMinutes && (
                <p className="text-xs text-destructive mt-1">{errors.intervalMinutes}</p>
              )}
              <div className="flex flex-wrap gap-2 mt-2">
                {PRESETS[type].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setInterval(n)}
                    className={cn(
                      "px-3 py-1 rounded-lg border text-sm font-medium transition-all duration-200",
                      interval === n
                        ? "bg-primary text-primary-foreground border-primary shadow-soft"
                        : "border-border bg-background text-foreground hover:bg-secondary"
                    )}
                  >
                    {n} мин
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Предпросмотр */}
          <div className="p-4 rounded-lg bg-gradient-to-br from-primary/5 to-primary/10 border border-primary/20">
            <h3 className="text-sm font-medium text-foreground mb-2">Предпросмотр</h3>
            <div className="text-sm text-muted-foreground">
              <span className="text-lg mr-2">{typeInfo.emoji}</span>
              {title.trim() || typeInfo.label}, {time}
              {interval && ` • каждые ${interval} мин`}
            </div>
          </div>

          {/* Кнопки */}
          <div className="flex gap-3 pt-4">
            <MedicalButton
              type="button"
              variant="outline"
              className="flex-1"
              onClick={() => navigate("/reminders")}
            >
              Отмена
            </MedicalButton>
            <MedicalButton 
              type="submit" 
              disabled={!formValid}
              className="flex-1"
              variant="medical"
            >
              {editing ? "Обновить" : "Создать"}
            </MedicalButton>
          </div>
        </form>

        {/* Модальное окно выбора типа */}
        <Sheet open={typeOpen} onClose={() => setTypeOpen(false)}>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">Выберите тип напоминания</h3>
            <div className="grid grid-cols-2 gap-3">
              {(Object.keys(TYPES) as NormalizedReminderType[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    setType(key);
                    setTypeOpen(false);
                  }}
                  className="medical-tile animate-scale-in p-4"
                >
                  <div className="text-3xl mb-2">{TYPES[key].emoji}</div>
                  <div className="text-sm font-medium text-foreground">{TYPES[key].label}</div>
                </button>
              ))}
            </div>
          </div>
        </Sheet>
      </main>
    </div>
  );
}

