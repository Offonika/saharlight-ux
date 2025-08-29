import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ReminderSchema } from "@sdk";
import { useRemindersApi } from "../api/reminders";
import { formatNextAt } from "../../../shared/datetime";
import { useTelegram } from "@/hooks/useTelegram";
import { useToast } from "@/hooks/use-toast";
import { Templates } from "../components/Templates";
import { bulkToggle } from "./RemindersList.bulk";

const checkQuotaLimit = (count: number, limit: number, toast: any) => {
  if (count >= limit) {
    toast({ title: "Лимит достигнут", description: `Достигнут лимит ${limit} напоминаний. Обновитесь до Pro для увеличения лимита!`, variant: "destructive" });
    return false;
  }
  return true;
};

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
  // Приоритет определения расписания:
  // 1. Если есть time - это напоминание на время
  if (r.time) return `в ${r.time}`;
  // 2. Если есть intervalMinutes - это повторяющееся напоминание
  if (r.intervalMinutes) return `каждые ${r.intervalMinutes} мин`;
  // 3. Если есть minutesAfter - это напоминание после события
  if (r.minutesAfter) return `после еды • через ${r.minutesAfter} мин`;
  // 4. Fallback - показываем тип напоминания
  return TYPE_LABEL[r.type] || "Напоминание";
}

export default function RemindersList({
  onCountChange,
  planLimit,
  onLimitChange
}: {
  onCountChange?: (count: number) => void;
  planLimit?: number;
  onLimitChange?: (limit: number) => void;
} = {}) {
  const api = useRemindersApi();
  const { user } = useTelegram();
  const navigate = useNavigate();
  const { toast } = useToast();
  const isDev = import.meta.env.DEV;
  const [items, setItems] = useState<ReminderDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPlanLimit, setCurrentPlanLimit] = useState<number>(planLimit || 5);
  const [filter, setFilter] = useState<"all" | "on" | "off">(() => {
    return (localStorage.getItem('reminderFilter') as "all" | "on" | "off") || "all";
  });

  async function load() {
    if (!user?.id) return;
    setLoading(true);
    try {
      const res = await api.remindersGetRaw({ telegramId: user.id });
      const data = await res.value();
      setItems(data as any);

      const limitHeader =
        res.raw.headers.get("X-Plan-Limit") ?? res.raw.headers.get("x-plan-limit");
      if (limitHeader) {
        const limit = parseInt(limitHeader, 10);
        if (!isNaN(limit)) {
          setCurrentPlanLimit(limit);
          onLimitChange?.(limit);
        }
      }
    } catch (error) {
      if (isDev) {
        console.warn("Backend API failed:", error);
      }
      toast({ title: "Ошибка", description: "Не удалось загрузить напоминания", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }
  
  useEffect(() => { 
    load(); 
  }, [user?.id]);
  
  // Update count when items change
  useEffect(() => {
    onCountChange?.(items.length);
  }, [items.length, onCountChange]);
  
  // Update limit when prop changes
  useEffect(() => {
    if (planLimit) {
      setCurrentPlanLimit(planLimit);
    }
  }, [planLimit]);

  const groups = useMemo(() => {
    // Filter items based on current filter
    const filteredItems = items.filter(r => 
      filter === "all" || (filter === "on" ? r.isEnabled : !r.isEnabled)
    );
    
    const map = new Map<string, ReminderDto[]>();
    for (const r of filteredItems) {
      const k = r.type || "custom";
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(r);
    }
    return Array.from(map.entries());
  }, [items, filter]);

  async function toggleEnabled(r: ReminderDto) {
    const optimistic = items.map(x =>
      x.id === r.id ? { ...x, isEnabled: !x.isEnabled } : x
    );
    setItems(optimistic);
    try {
      try {
        const reminder: ReminderSchema = {
          telegramId: r.telegramId,
          id: r.id,
          type: r.type as any,
          kind: r.kind,
          time: r.time ?? undefined,
          intervalMinutes: r.intervalMinutes ?? undefined,
          minutesAfter: r.minutesAfter ?? undefined,
          daysOfWeek: r.daysOfWeek ?? undefined,
          isEnabled: !r.isEnabled,
        };
        await api.remindersPatch({ reminder });
      } catch (apiError) {
        if (isDev) {
          console.warn("Backend API failed, using mock API:", apiError);
          const { mockApi } = await import("../../../api/mock-server");
          await mockApi.updateReminder({ ...r, isEnabled: !r.isEnabled });
        } else {
          throw apiError;
        }
      }
      load();
    } catch {
      setItems(items);
      toast({ title: "Ошибка", description: "Не удалось обновить статус", variant: "destructive" });
    }
  }

  const handleFilterChange = (newFilter: "all" | "on" | "off") => {
    setFilter(newFilter);
    localStorage.setItem('reminderFilter', newFilter);
  };

  const handleBulkToggle = async (enable: boolean) => {
    if (!items.length) return;
    
    const action = enable ? "включить" : "выключить";
    const itemsToChange = items.filter(r => r.isEnabled !== enable);
    
    if (!itemsToChange.length) {
      toast({ title: "Готово", description: `Все напоминания уже ${enable ? "включены" : "выключены"}` });
      return;
    }

    setLoading(true);
    try {
      const result = await bulkToggle(api, itemsToChange, enable);
      
      if (result.successCount > 0) {
        toast({ title: "Успешно", description: `Успешно ${enable ? "включено" : "выключено"} ${result.successCount} напоминаний` });
      }
      
      if (result.errorCount > 0) {
        toast({ title: "Частично выполнено", description: `Не удалось ${action} ${result.errorCount} напоминаний`, variant: "destructive" });
      }
      
      // Reload to get fresh data
      await load();
    } catch (error) {
      toast({ title: "Ошибка", description: `Ошибка при попытке ${action} напоминания`, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const filterOptions = [
    { value: "all" as const, label: "Все", count: items.length },
    { value: "on" as const, label: "Вкл", count: items.filter(r => r.isEnabled).length },
    { value: "off" as const, label: "Выкл", count: items.filter(r => !r.isEnabled).length }
  ];

  async function remove(r: ReminderDto) {
    if (!confirm("Удалить напоминание?")) return;
    const optimistic = items.filter(x => x.id !== r.id);
    setItems(optimistic);
    try {
      try {
        await api.remindersDelete({ telegramId: r.telegramId, id: r.id });
      } catch (apiError) {
        if (isDev) {
          console.warn("Backend API failed, using mock API:", apiError);
          const { mockApi } = await import("../../../api/mock-server");
          await mockApi.deleteReminder(r.telegramId, r.id);
        } else {
          throw apiError;
        }
      }
    } catch {
      toast({ title: "Ошибка", description: "Не удалось удалить", variant: "destructive" });
      setItems(items);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {user?.id && (
        <Templates 
          telegramId={user.id} 
          onCreated={() => {
            if (checkQuotaLimit(items.length, currentPlanLimit, toast)) {
              load();
            }
          }} 
        />
      )}

      {/* Filter Chips */}
      {items.length > 0 && (
        <div className="space-y-3">
          <div className="flex gap-2 flex-wrap">
            {filterOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => handleFilterChange(option.value)}
                className={`px-3 py-2 rounded-lg border text-sm font-medium transition-all duration-200 ${
                  filter === option.value
                    ? "bg-primary text-primary-foreground border-primary shadow-soft"
                    : "border-border bg-background text-foreground hover:bg-secondary hover:border-primary/20"
                }`}
              >
                {option.label} ({option.count})
              </button>
            ))}
          </div>
          
          {/* Bulk Actions */}
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => handleBulkToggle(true)}
              disabled={loading}
              className="px-3 py-2 rounded-lg border border-border bg-background text-foreground hover:bg-secondary hover:border-primary/20 transition-all duration-200 text-sm font-medium disabled:opacity-50"
            >
              ✅ Включить все
            </button>
            <button
              onClick={() => handleBulkToggle(false)}
              disabled={loading}
              className="px-3 py-2 rounded-lg border border-border bg-background text-foreground hover:bg-secondary hover:border-primary/20 transition-all duration-200 text-sm font-medium disabled:opacity-50"
            >
              ❌ Выключить все
            </button>
          </div>
        </div>
      )}
      
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
                    <button
                      type="button"
                      onClick={() => navigate(`/reminders/${r.id}/edit`)}
                      className="px-3 py-1 rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-all duration-200"
                    >
                      ✏️
                    </button>
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
          <button
            type="button"
            onClick={() => navigate('/reminders/new')}
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            + Добавить первое напоминание
          </button>
        </div>
      )}
    </div>
  );
}