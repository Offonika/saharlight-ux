import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRemindersApi } from "../api/reminders"; // ваш хук, возвращающий RemindersApi
import { DayOfWeekPicker } from "../components/DayOfWeekPicker";
import { DaysPresets } from "../components/DaysPresets";
import { buildReminderPayload, ReminderFormValues, ScheduleKind, ReminderType } from "../api/buildPayload";
import { validate, hasErrors } from "../logic/validate";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";
import { getTelegramUserId } from "../../../shared/telegram";
import { mockApi } from "../../../api/mock-server";
import { useToast } from "../../../shared/toast";

const TYPE_OPTIONS: { value: ReminderType; label: string }[] = [
  { value: "sugar", label: "Измерение сахара" },
  { value: "insulin_short", label: "Инсулин (короткий)" },
  { value: "insulin_long", label: "Инсулин (длинный)" },
  { value: "after_meal", label: "После еды" },
  { value: "meal", label: "Приём пищи" },
  { value: "sensor_change", label: "Смена сенсора" },
  { value: "injection_site", label: "Смена места инъекции" },
  { value: "custom", label: "Другое" },
];

const KIND_OPTIONS: { value: ScheduleKind; label: string }[] = [
  { value: "at_time", label: "Время" },
  { value: "every", label: "Каждые…" },
  { value: "after_event", label: "После события" },
];

export default function RemindersCreate() {
  const api = useRemindersApi();
  const initData = useTelegramInitData();
  const telegramId = useMemo(() => getTelegramUserId(initData), [initData]);
  const nav = useNavigate();
  const toast = useToast();

  const [form, setForm] = useState<ReminderFormValues>({
    telegramId,
    type: "sugar",
    kind: "at_time",
    time: "07:30",
    isEnabled: true,
  });
  const [loading, setLoading] = useState(false);

  const errors = validate(form);
  const formHasErrors = hasErrors(errors);

  const onChange = <K extends keyof ReminderFormValues>(k: K, v: ReminderFormValues[K]) =>
    setForm((s) => ({ ...s, [k]: v }));

  const presetsTime = ["07:30","12:30","22:00"];
  const presetsEvery = [60,120,180,1440];
  const presetsAfter = [90,120,150];

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (formHasErrors) return;
    
    setLoading(true);
    try {
      const payload = buildReminderPayload({ ...form, telegramId });
      console.log("Payload being sent:", payload);
      
      try {
        // Пробуем основной API
        await api.remindersPost({ reminder: payload });
      } catch (apiError) {
        console.warn("Backend API failed, using mock API:", apiError);
        // Fallback на mock API
        await mockApi.createReminder(payload);
      }
      
      toast.success("Напоминание успешно создано");
      nav("/reminders");
    } catch (err) {
      console.error("Error saving reminder:", err);
      toast.error("Ошибка: не удалось сохранить напоминание");
    } finally {
      setLoading(false);
    }
  }

  // switchKind: фиксируем type и поля расписания  
  const switchKind = (k: ScheduleKind) =>
    setForm(s => {
      const base = { ...s, kind: k, time: undefined, intervalMinutes: undefined, minutesAfter: undefined };
      if (k === "at_time") base.time = "07:30";
      if (k === "every") base.intervalMinutes = 60;
      if (k === "after_event") { base.minutesAfter = 120; base.type = "after_meal"; }
      return base;
    });

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <div className="container mx-auto px-4 py-6">
        <form className="max-w-xl mx-auto space-y-6 medical-card animate-slide-up" onSubmit={onSubmit}>
          <h1 className="text-xl font-semibold text-foreground">Добавить напоминание</h1>

          {/* Тип */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Тип</label>
            <select
              className="medical-input"
              value={form.kind === "after_event" ? "after_meal" : form.type}
              onChange={(e) => onChange("type", e.target.value as ReminderType)}
              disabled={form.kind === "after_event"}
            >
              {TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            {form.kind === "after_event" && (
              <p className="text-xs text-muted-foreground mt-1">
                Это напоминание сработает <strong className="text-foreground">после записи приёма пищи</strong> в разделе «История».
              </p>
            )}
          </div>

          {/* Режим */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Режим</label>
            <div className="flex gap-2">
              {KIND_OPTIONS.map((o) => (
                <button
                  type="button" 
                  key={o.value}
                  onClick={() => switchKind(o.value)}
                  className={`px-3 py-2 rounded-lg border transition-all duration-200 ${
                    form.kind === o.value 
                      ? "bg-primary text-primary-foreground border-primary shadow-soft" 
                      : "border-border bg-background text-foreground hover:bg-secondary"
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Условные поля */}
          {form.kind === "at_time" && (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-foreground">Время (HH:MM)</label>
              <input
                type="time"
                className={`medical-input ${errors.time ? "border-destructive focus:border-destructive" : ""}`}
                value={form.time || ""}
                onChange={(e) => onChange("time", e.target.value)}
              />
              {errors.time && (
                <p className="text-xs text-destructive mt-1">{errors.time}</p>
              )}
              <div className="flex gap-2 flex-wrap">
                {presetsTime.map((t) => (
                  <button 
                    key={t} 
                    type="button" 
                    className="px-3 py-1 rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-colors" 
                    onClick={() => onChange("time", t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          )}

          {form.kind === "every" && (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-foreground">Интервал (мин)</label>
              <input
                type="number" 
                min={1}
                className={`medical-input ${errors.intervalMinutes ? "border-destructive focus:border-destructive" : ""}`}
                value={form.intervalMinutes ?? ""}
                onChange={(e) => onChange("intervalMinutes", Number(e.target.value || 0))}
              />
              {errors.intervalMinutes && (
                <p className="text-xs text-destructive mt-1">{errors.intervalMinutes}</p>
              )}
              <div className="flex gap-2 flex-wrap">
                {presetsEvery.map((m) => (
                  <button 
                    key={m} 
                    type="button" 
                    className="px-3 py-1 rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-colors" 
                    onClick={() => onChange("intervalMinutes", m)}
                  >
                    {m} мин
                  </button>
                ))}
              </div>
            </div>
          )}

          {form.kind === "after_event" && (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-foreground">Задержка после еды (мин)</label>
              <input
                type="number" 
                min={1}
                className={`medical-input ${errors.minutesAfter ? "border-destructive focus:border-destructive" : ""}`}
                value={form.minutesAfter ?? ""}
                onChange={(e) => onChange("minutesAfter", Number(e.target.value || 0))}
              />
              {errors.minutesAfter && (
                <p className="text-xs text-destructive mt-1">{errors.minutesAfter}</p>
              )}
              <div className="flex gap-2 flex-wrap">
                {presetsAfter.map((m) => (
                  <button 
                    key={m} 
                    type="button" 
                    className="px-3 py-1 rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-colors" 
                    onClick={() => onChange("minutesAfter", m)}
                  >
                    {m} мин
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Дни недели */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Дни недели (опционально)</label>
            <div className="space-y-3">
              <DaysPresets value={form.daysOfWeek} onChange={(v) => onChange("daysOfWeek", v)} />
              <DayOfWeekPicker value={form.daysOfWeek} onChange={(v) => onChange("daysOfWeek", v)} />
            </div>
          </div>

          {/* Название (необяз.) */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Название (если пусто — автогенерация)</label>
            <input
              className="medical-input"
              value={form.title ?? ""}
              onChange={(e) => onChange("title", e.target.value)}
              placeholder="Напр.: Сахар утром"
            />
          </div>

          {/* Вкл/Выкл */}
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.isEnabled ?? true}
              onChange={(e) => onChange("isEnabled", e.target.checked)}
              className="rounded border-border focus:ring-ring"
            />
            <span className="text-foreground">Включено</span>
          </label>

          <button 
            disabled={loading || formHasErrors} 
            className="w-full bg-primary text-primary-foreground rounded-xl py-3 shadow-soft hover:shadow-medium hover:bg-primary/90 disabled:opacity-50 transition-all duration-200"
          >
            {loading ? "Сохранение…" : "Сохранить"}
          </button>
        </form>
      </div>
    </div>
  );
}