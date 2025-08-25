import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRemindersApi } from "../api/reminders"; // ваш хук, возвращающий DefaultApi
import { DayOfWeekPicker } from "../components/DayOfWeekPicker";
import { buildReminderPayload, ReminderFormValues, ScheduleKind, ReminderType } from "../api/buildPayload";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";
import { getTelegramUserId } from "../../../shared/telegram";
import { mockApi } from "../../../api/mock-server";

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

  const [form, setForm] = useState<ReminderFormValues>({
    telegramId,
    type: "sugar",
    kind: "at_time",
    time: "07:30",
    isEnabled: true,
  });
  const [loading, setLoading] = useState(false);

  const onChange = <K extends keyof ReminderFormValues>(k: K, v: ReminderFormValues[K]) =>
    setForm((s) => ({ ...s, [k]: v }));

  const presetsTime = ["07:30","12:30","22:00"];
  const presetsEvery = [60,120,180,1440];
  const presetsAfter = [90,120,150];

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
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
      
      nav("/reminders");
    } catch (err) {
      console.error("Error saving reminder:", err);
      alert("Ошибка: не удалось сохранить напоминание");
    } finally {
      setLoading(false);
    }
  }

  // Гарантируем «ровно одно» поле
  const clearScheduleFields = (nextKind: ScheduleKind) => {
    setForm(s => {
      const base = { ...s, kind: nextKind, time: undefined, intervalMinutes: undefined, minutesAfter: undefined };
      if (nextKind === "at_time") base.time = "07:30";
      if (nextKind === "every") base.intervalMinutes = 60;
      if (nextKind === "after_event") base.minutesAfter = 120;
      return base;
    });
  };

  return (
    <form className="max-w-xl mx-auto p-4 space-y-4" onSubmit={onSubmit}>
      <h1 className="text-xl font-semibold">Добавить напоминание</h1>

      {/* Тип */}
      <label className="block text-sm font-medium">Тип</label>
      <select
        className="w-full border rounded-lg px-3 py-2"
        value={form.type}
        onChange={(e) => onChange("type", e.target.value as ReminderType)}
      >
        {TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>

      {/* Режим */}
      <label className="block text-sm font-medium">Режим</label>
      <div className="flex gap-2">
        {KIND_OPTIONS.map((o) => (
          <button
            type="button" key={o.value}
            onClick={() => clearScheduleFields(o.value)}
            className={`px-3 py-1 rounded-2xl border ${form.kind===o.value?"bg-black text-white border-black":"border-gray-300"}`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {/* Условные поля */}
      {form.kind === "at_time" && (
        <>
          <label className="block text-sm font-medium">Время (HH:MM)</label>
          <input
            type="time"
            className="w-full border rounded-lg px-3 py-2"
            value={form.time || ""}
            onChange={(e) => onChange("time", e.target.value)}
          />
          <div className="flex gap-2">
            {presetsTime.map((t) => (
              <button key={t} type="button" className="px-3 py-1 rounded-2xl border border-gray-300" onClick={() => onChange("time", t)}>{t}</button>
            ))}
          </div>
        </>
      )}

      {form.kind === "every" && (
        <>
          <label className="block text-sm font-medium">Интервал (мин)</label>
          <input
            type="number" min={1}
            className="w-full border rounded-lg px-3 py-2"
            value={form.intervalMinutes ?? ""}
            onChange={(e) => onChange("intervalMinutes", Number(e.target.value || 0))}
          />
          <div className="flex gap-2">
            {presetsEvery.map((m) => (
              <button key={m} type="button" className="px-3 py-1 rounded-2xl border border-gray-300" onClick={() => onChange("intervalMinutes", m)}>{m} мин</button>
            ))}
          </div>
        </>
      )}

      {form.kind === "after_event" && (
        <>
          <label className="block text-sm font-medium">Задержка (мин)</label>
          <input
            type="number" min={1}
            className="w-full border rounded-lg px-3 py-2"
            value={form.minutesAfter ?? ""}
            onChange={(e) => onChange("minutesAfter", Number(e.target.value || 0))}
          />
          <div className="flex gap-2">
            {presetsAfter.map((m) => (
              <button key={m} type="button" className="px-3 py-1 rounded-2xl border border-gray-300" onClick={() => onChange("minutesAfter", m)}>{m} мин</button>
            ))}
          </div>
        </>
      )}

      {/* Дни недели */}
      <div>
        <label className="block text-sm font-medium mb-1">Дни недели (опционально)</label>
        <DayOfWeekPicker value={form.daysOfWeek} onChange={(v)=>onChange("daysOfWeek", v)} />
      </div>

      {/* Название (необяз.) */}
      <label className="block text-sm font-medium">Название (если пусто — автогенерация)</label>
      <input
        className="w-full border rounded-lg px-3 py-2"
        value={form.title ?? ""}
        onChange={(e) => onChange("title", e.target.value)}
        placeholder="Напр.: Сахар утром"
      />

      {/* Вкл/Выкл */}
      <label className="inline-flex items-center gap-2">
        <input
          type="checkbox"
          checked={form.isEnabled ?? true}
          onChange={(e) => onChange("isEnabled", e.target.checked)}
        />
        Включено
      </label>

      <button disabled={loading} className="w-full bg-black text-white rounded-xl py-3 disabled:opacity-50">
        {loading ? "Сохранение…" : "Сохранить"}
      </button>
    </form>
  );
}