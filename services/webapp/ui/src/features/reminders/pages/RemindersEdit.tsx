import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { ReminderSchema } from "@sdk";
import { useRemindersApi } from "../api/reminders";
import { DayOfWeekPicker } from "../components/DayOfWeekPicker";
import { DaysPresets } from "../components/DaysPresets";
import AfterEventDelay from "../components/AfterEventDelay";
import { buildReminderPayload } from "../api/buildPayload";
import type { ReminderDto, ScheduleKind, ReminderType } from "../types";
import { validate, hasErrors } from "../logic/validate";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";
import { setTelegramInitData } from "@/lib/telegram-auth";
import { getTelegramUserId } from "../../../shared/telegram";
import { useToast } from "../../../shared/toast";
import { useTelegram } from "@/hooks/useTelegram";
import TimeInput from "@/components/TimeInput";

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

function mapToForm(reminder: ReminderSchema): ReminderDto {
  const kind: ScheduleKind =
    (reminder.kind as ScheduleKind | undefined) ||
    (reminder.time
      ? "at_time"
      : reminder.intervalMinutes
      ? "every"
      : reminder.minutesAfter
      ? "after_event"
      : "at_time");
  return {
    telegramId: reminder.telegramId,
    type: reminder.type as ReminderType,
    kind,
    time: reminder.time?.slice(0, 5) ?? undefined,
    intervalMinutes: reminder.intervalMinutes ?? undefined,
    minutesAfter: reminder.minutesAfter ?? undefined,
    daysOfWeek: reminder.daysOfWeek
      ? Array.from(reminder.daysOfWeek)
      : undefined,
    title: reminder.title ?? undefined,
    isEnabled: reminder.isEnabled ?? true,
  };
}

export default function RemindersEdit() {
  const api = useRemindersApi();
  const initData = useTelegramInitData();
  useEffect(() => {
    if (initData) {
      setTelegramInitData(initData);
    }
  }, [initData]);
  const { sendData, user } = useTelegram();
  const telegramId = useMemo(
    () => getTelegramUserId(initData) || user?.id || 0,
    [initData, user],
  );
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState<ReminderDto | null>(null);
  const [saving, setSaving] = useState(false);

  const presetsTime = ["07:30", "12:30", "22:00"];
  const presetsEvery = [60, 120, 180, 1440];

  useEffect(() => {
    async function load() {
      if (!id || !telegramId) return;
      try {
        let reminder: ReminderSchema;
        try {
          reminder = await api.remindersIdGet({ id: Number(id), telegramId });
        } catch (apiError) {
          if (import.meta.env.DEV) {
            console.warn("Backend API failed:", apiError);
          }
          throw apiError;
        }
        setForm(mapToForm(reminder));
      } catch (err) {
        console.error("Error loading reminder:", err);
        toast.error("Не удалось загрузить напоминание");
      }
    }
    load();
  }, [api, id, telegramId, toast]);

  if (!form) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20 flex items-center justify-center">
        <p className="text-muted-foreground">Загрузка…</p>
      </div>
    );
  }

  const errors = validate(form);
  const formHasErrors = hasErrors(errors);

  const onChange = <K extends keyof ReminderDto>(
    k: K,
    v: ReminderDto[K],
  ) => setForm((s) => (s ? { ...s, [k]: v } : s));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (formHasErrors || !id) return;

    setSaving(true);
    try {
      const reminder: ReminderSchema = {
        ...buildReminderPayload({ ...form, telegramId }),
        id: Number(id),
      };

      try {
        await api.remindersPatch({ reminder });
      } catch (apiError) {
        if (import.meta.env.DEV) {
          console.warn("Backend API failed:", apiError);
        }
        throw apiError;
      }

      const value = form.time
        ? form.time
        : form.intervalMinutes
        ? `${form.intervalMinutes}m`
        : form.minutesAfter
        ? `${form.minutesAfter}m`
        : "";
      sendData?.({ id: Number(id), type: form.type, value });

      toast.success("Напоминание успешно обновлено");
      nav("/reminders");
    } catch (err) {
      console.error("Error updating reminder:", err);
      toast.error("Ошибка: не удалось сохранить напоминание");
    } finally {
      setSaving(false);
    }
  }

  const switchKind = (k: ScheduleKind) =>
    setForm((s) => {
      if (!s) return s;
      const base = {
        ...s,
        kind: k,
        time: undefined,
        intervalMinutes: undefined,
        minutesAfter: undefined,
      };
      if (k === "at_time") base.time = "07:30";
      if (k === "every") base.intervalMinutes = 60;
      if (k === "after_event") {
        base.minutesAfter = 120;
        base.type = "after_meal";
      }
      return base;
    });

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <div className="container mx-auto px-4 py-6">
        <form
          className="max-w-xl mx-auto space-y-6 medical-card animate-slide-up"
          onSubmit={onSubmit}
        >
          <h1 className="text-xl font-semibold text-foreground">
            Редактировать напоминание
          </h1>

          {/* Тип */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Тип
            </label>
            <select
              className="medical-input"
              value={form.kind === "after_event" ? "after_meal" : form.type}
              onChange={(e) => onChange("type", e.target.value as ReminderType)}
              disabled={form.kind === "after_event"}
            >
              {TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            {form.kind === "after_event" && (
              <p className="text-xs text-muted-foreground mt-1">
                Это напоминание сработает
                <strong className="text-foreground">
                  {" "}после записи приёма пищи{" "}
                </strong>
                в разделе «История».
              </p>
            )}
          </div>

          {/* Режим */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Режим
            </label>
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
              <label className="block text-sm font-medium text-foreground">
                Время (HH:MM)
              </label>
              <TimeInput
                className={`medical-input ${
                  errors.time ? "border-destructive focus:border-destructive" : ""
                }`}
                value={form.time || ""}
                onChange={(val) => onChange("time", val)}
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
              <label className="block text-sm font-medium text-foreground">
                Интервал (мин)
              </label>
              <input
                type="number"
                className={`medical-input ${
                  errors.intervalMinutes
                    ? "border-destructive focus:border-destructive"
                    : ""
                }`}
                value={form.intervalMinutes?.toString() || ""}
                onChange={(e) =>
                  onChange("intervalMinutes", Number(e.target.value))
                }
              />
              {errors.intervalMinutes && (
                <p className="text-xs text-destructive mt-1">
                  {errors.intervalMinutes}
                </p>
              )}
              <div className="flex gap-2 flex-wrap">
                {presetsEvery.map((t) => (
                  <button
                    key={t}
                    type="button"
                    className="px-3 py-1 rounded-lg border border-border bg-background text-foreground hover:bg-secondary transition-colors"
                    onClick={() => onChange("intervalMinutes", t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          )}

          {form.kind === "after_event" && (
            <AfterEventDelay
              value={form.minutesAfter}
              onChange={(v) => onChange("minutesAfter", v)}
              error={errors.minutesAfter}
            />
          )}

          {/* Дни недели */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Дни недели (опционально)
            </label>
            <div className="space-y-3">
              <DaysPresets
                value={form.daysOfWeek}
                onChange={(v) => onChange("daysOfWeek", v)}
              />
              <DayOfWeekPicker
                value={form.daysOfWeek}
                onChange={(v) => onChange("daysOfWeek", v)}
              />
            </div>
          </div>

          {/* Название (необяз.) */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Название (если пусто — автогенерация)
            </label>
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
            disabled={saving || formHasErrors}
            className="w-full bg-primary text-primary-foreground rounded-xl py-3 shadow-soft hover:shadow-medium hover:bg-primary/90 disabled:opacity-50 transition-all duration-200"
          >
            {saving ? "Сохранение…" : "Сохранить"}
          </button>
        </form>
      </div>
    </div>
  );
}
