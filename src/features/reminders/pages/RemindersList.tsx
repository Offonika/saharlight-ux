import React, { useEffect, useMemo, useState } from "react";
import { useRemindersApi } from "../api/reminders";
import { formatNextAt } from "../../../shared/datetime";
import { useTelegram } from "@/hooks/useTelegram";
import { mockApi } from "../../../api/mock-server";
import { useToast } from "../../../shared/toast";

type ReminderDto = {
  id: number;
  telegramId: number;
  type: string;
  title?: string | null;
  kind: "at_time" | "every" | "after_event";
  time?: string | null;
  intervalMinutes?: number | null;
  minutesAfter?: number | null;
  daysOfWeek?: number[] | null;
  isEnabled: boolean;
  nextAt?: string | null;
};

const TYPE_LABEL: Record<string, string> = {
  sugar: "Измерение сахара",
  insulin_short: "Инсулин (короткий)",
  insulin_long: "Инсулин (длинный)",
  after_meal: "После еды",
  meal: "Приём пищи",
  sensor_change: "Смена сенсора",
  injection_site: "Смена места инъекции",
  custom: "Другое",
};

function scheduleLine(r: ReminderDto) {
  if (r.kind === "at_time" && r.time) return `в ${r.time}`;
  if (r.kind === "every" && r.intervalMinutes) return `каждые ${r.intervalMinutes} мин`;
  if (r.kind === "after_event" && r.minutesAfter) return `после еды • через ${r.minutesAfter} мин`;
  return "";
}

export default function RemindersList() {
  const api = useRemindersApi();
  const { user } = useTelegram();
  const toast = useToast();
  const [items, setItems] = useState<ReminderDto[]>([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    if (!user?.id) return;
    setLoading(true);
    try {
      try {
        const res = await api.remindersGet({ telegramId: user.id });
        setItems(res as any);
      } catch (apiError) {
        console.warn("Backend API failed, using mock API:", apiError);
        const res = await mockApi.getReminders(user.id);
        setItems(res as any);
      }
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, [user?.id]);

  const groups = useMemo(() => {
    const map = new Map<string, ReminderDto[]>();
    for (const r of items) {
      const k = r.type || "custom";
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(r);
    }
    return Array.from(map.entries());
  }, [items]);

  async function toggleEnabled(r: ReminderDto) {
    const optimistic = items.map(x => x.id === r.id ? { ...x, isEnabled: !x.isEnabled } : x);
    setItems(optimistic);
    try {
      try {
        await api.remindersPatch({ reminder: { telegramId: r.telegramId, id: r.id, isEnabled: !r.isEnabled } });
      } catch (apiError) {
        console.warn("Backend API failed, using mock API:", apiError);
        await mockApi.updateReminder({ ...r, isEnabled: !r.isEnabled });
      }
      load();
    } catch {
      setItems(items);
      toast.error("Не удалось обновить статус");
    }
  }

  async function remove(r: ReminderDto) {
    if (!confirm("Удалить напоминание?")) return;
    const optimistic = items.filter(x => x.id !== r.id);
    setItems(optimistic);
    try {
      try {
        await api.remindersDelete({ telegramId: r.telegramId, id: r.id });
      } catch (apiError) {
        console.warn("Backend API failed, using mock API:", apiError);
        await mockApi.deleteReminder(r.telegramId, r.id);
      }
    } catch {
      toast.error("Не удалось удалить");
      setItems(items);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-pulse text-center">
            <div className="w-8 h-8 rounded-full bg-primary/20 mx-auto mb-2"></div>
            <p className="text-muted-foreground">Загрузка напоминаний...</p>
          </div>
        </div>
      )}

      {!loading && groups.map(([type, arr]) => (
        <div key={type} className="space-y-3 animate-fade-in">
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
            {TYPE_LABEL[type] ?? "Другое"}
          </h2>
          <div className="space-y-3">
            {arr.map((r, index) => (
              <div 
                key={r.id} 
                className="medical-list-item animate-slide-up"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-card-foreground truncate">
                      {r.title || TYPE_LABEL[r.type] || "Напоминание"}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {scheduleLine(r)}
                    </div>
                    <div className="text-xs text-muted-foreground/70">
                      Следующее: {formatNextAt(r.nextAt)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button 
                      onClick={() => toggleEnabled(r)} 
                      className={`px-3 py-1 rounded-lg border transition-all duration-200 text-sm font-medium ${
                        r.isEnabled 
                          ? "bg-primary text-primary-foreground border-primary shadow-soft hover:shadow-medium" 
                          : "border-border bg-background text-foreground hover:bg-secondary"
                      }`}
                    >
                      {r.isEnabled ? "Вкл." : "Выкл."}
                    </button>
                    <a 
                      href={`/reminders/${r.id}/edit`} 
                      className="px-3 py-1 rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-all duration-200"
                    >
                      ✏️
                    </a>
                    <button 
                      onClick={() => remove(r)} 
                      className="px-3 py-1 rounded-lg border border-border bg-background text-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/20 transition-all duration-200"
                    >
                      🗑
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {!loading && !items.length && (
        <div className="text-center py-12 animate-fade-in">
          <div className="w-16 h-16 rounded-full bg-muted/50 mx-auto mb-4 flex items-center justify-center">
            <span className="text-2xl">⏰</span>
          </div>
          <p className="text-muted-foreground">Пока нет напоминаний</p>
          <a 
            href="/reminders/new" 
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            + Добавить первое напоминание
          </a>
        </div>
      )}
    </div>
  );
}