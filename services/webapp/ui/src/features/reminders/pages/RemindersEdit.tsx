import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useRemindersApi } from "../api/reminders";
import { DayOfWeekPicker } from "../components/DayOfWeekPicker";
import {
  buildReminderPayload,
  type ReminderFormValues,
  type ScheduleKind,
  type ReminderType,
} from "../api/buildPayload";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";

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

function getTelegramUserId(initData: string): number {
  try {
    const raw = new URLSearchParams(initData).get("user");
    if (!raw) return 0;
    const u = JSON.parse(decodeURIComponent(raw));
    return Number(u?.id ?? 0);
  } catch {
    return 0;
  }
}

function schedulePreview(f: ReminderFormValues) {
  const map: Record<ReminderType, string> = {
    sugar: "Сахар",
    insulin_short: "Короткий инсулин",
    insulin_long: "Длинный инсулин",
    after_meal: "После еды",
    meal: "Приём пищи",
    sensor_change: "Смена сенсора",
    injection_site: "Смена места инъекции",
    custom: "Напоминание",
  };
  const title = f.title?.trim() || map[f.type] || "Напоминание";
  if (f.kind === "at_time" && f.time) return `🔴 ${title}, ${f.time}`;
  if (f.kind === "every" && f.intervalMinutes) return `🔔 ${title} • каждые ${f.intervalMinutes} мин`;
  if (f.kind === "after_event" && f.minutesAfter) return `🍽 ${title} • через ${f.minutesAfter} мин (после еды)`;
  return title;
}

export default function RemindersEdit() {
  const { id } = useParams();
  const api = useRemindersApi();
  const initData = useTelegramInitData();
  const telegramId = useMemo(() => getTelegramUserId(initData), [initData]);
  const nav = useNavigate();

  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<ReminderFormValues | null>(null);
  const [isDirty, setDirty] = useState(false);

  const onChange = <K extends keyof ReminderFormValues>(k: K, v: ReminderFormValues[K]) => {
    setDirty(true);
    setForm((s) => (s ? { ...s, [k]: v } : s));
  };

  const switchKind = (k: ScheduleKind) =>
    setForm((s) =>
      s
        ? {
            ...s,
            kind: k,
            time: k === "at_time" ? (s.time ?? "07:30") : undefined,
            intervalMinutes: k === "every" ? (s.intervalMinutes ?? 60) : undefined,
            minutesAfter: k === "after_event" ? (s.minutesAfter ?? 120) : undefined,
            type: k === "after_event" ? "after_meal" : s.type,
          }
        : s
    );

  useEffect(() => {
    (async () => {
      try {
        const dto: any = await api.remindersIdGet(Number(id), { telegramId } as any);
        // backend уже возвращает kind; на всякий случай определим fallback
        const detectedKind: ScheduleKind =
          dto.kind ||
          (dto.time ? "at_time" : dto.intervalMinutes || dto.intervalHours ? "every" : "after_event");

        const fv: ReminderFormValues = {
          telegramId,
          type: (detectedKind === "after_event" ? "after_meal" : dto.type) as ReminderType,
          kind: detectedKind,
          time: dto.time ?? undefined,
          intervalMinutes: dto.intervalMinutes ?? (dto.intervalHours ? dto.intervalHours * 60 : undefined),
          minutesAfter: dto.minutesAfter ?? undefined,
          daysOfWeek: dto.daysOfWeek ?? undefined,
          title: dto.title ?? undefined,
          isEnabled: dto.isEnabled ?? true,
        };
        setForm(fv);
      } finally {
        setLoading(false);
      }
    })();
  }, [id, telegramId]);

  useEffect(() => {
    const h = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [isDirty]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;

    // простая фронт-валидация
    if (form.kind === "at_time" && !form.time) return alert("Укажите время (HH:MM)");
    if (form.kind === "every" && (!form.intervalMinutes || form.intervalMinutes < 1))
      return alert("Укажите интервал в минутах (>=1)");
    if (form.kind === "after_event" && (!form.minutesAfter || form.minutesAfter < 1))
      return alert("Укажите задержку после еды (>=1 мин)");

    try {
      const payload = { id: Number(id), ...buildReminderPayload({ ...form, telegramId }) };
      await api.remindersPatch(payload as any);
      setDirty(false);
      nav("/reminders");
    } catch (err: any) {
      const text = await err?.response?.text?.();
      console.error("PATCH /reminders failed", err?.response?.status, text);
      alert("Не удалось сохранить изменения");
    }
  }

  async function onDelete() {
    if (!confirm("Удалить напоминание?")) return;
    try {
      await api.remindersDelete({ telegramId, id: Number(id) } as any);
      nav("/reminders");
    } catch {
      alert("Удаление не удалось");
    }
  }

  if (loading || !form) return <div className="p-4">Загрузка…</div>;

  const presetsTime = ["07:30", "12:30", "22:00"];
  const presetsEvery = [60, 120, 180, 1440];
  const presetsAfter = [90, 120, 150];

  return (
    <form className="max-w-xl mx-auto p-4 space-y-4" onSubmit={onSave}>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Редактировать напоминание</h1>
        <button type="button" onClick={onDelete} className="px-3 py-2 rounded-lg border border-gray-300">
          🗑 Удалить
        </button>
      </div>

      {/* Тип */}
      <label className="block text-sm font-medium">Тип</label>
      <select
        className="w-full border rounded-lg px-3 py-2"
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
        <p className="text-xs text-gray-500">Сработает <b>после записи приёма пищи</b> в «Истории».</p>
      )}

      {/* Название */}
      <label className="block text-sm font-medium">Название (если пусто — автогенерация)</label>
      <input
        className="w-full border rounded-lg px-3 py-2"
        value={form.title ?? ""}
        onChange={(e) => onChange("title", e.target.value)}
      />

      {/* Режим */}
      <label className="block text-sm font-medium">Режим</label>
      <div className="flex gap-2">
        {KIND_OPTIONS.map((o) => (
          <button
            type="button"
            key={o.value}
            onClick={() => switchKind(o.value)}
            className={`px-3 py-1 rounded-2xl border ${
              form.kind === o.value ? "bg-black text-white border-black" : "border-gray-300"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {/* Поля по режиму */}
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
              <button
                key={t}
                type="button"
                className="px-3 py-1 rounded-2xl border border-gray-300"
                onClick={() => onChange("time", t)}
              >
                {t}
              </button>
            ))}
          </div>
        </>
      )}

      {form.kind === "every" && (
        <>
          <label className="block text-sm font-medium">Интервал (мин)</label>
          <input
            type="number"
            min={1}
            className="w-full border rounded-lg px-3 py-2"
            value={form.intervalMinutes ?? ""}
            onChange={(e) => onChange("intervalMinutes", Number(e.target.value || 0))}
          />
          <div className="flex gap-2">
            {presetsEvery.map((m) => (
              <button
                key={m}
                type="button"
                className="px-3 py-1 rounded-2xl border border-gray-300"
                onClick={() => onChange("intervalMinutes", m)}
              >
                {m} мин
              </button>
            ))}
          </div>
        </>
      )}

      {form.kind === "after_event" && (
        <>
          <label className="block text-sm font-medium">Задержка после еды (мин)</label>
          <input
            type="number"
            min={1}
            className="w-full border rounded-lg px-3 py-2"
            value={form.minutesAfter ?? ""}
            onChange={(e) => onChange("minutesAfter", Number(e.target.value || 0))}
          />
          <div className="flex gap-2">
            {presetsAfter.map((m) => (
              <button
                key={m}
                type="button"
                className="px-3 py-1 rounded-2xl border border-gray-300"
                onClick={() => onChange("minutesAfter", m)}
              >
                {m} мин
              </button>
            ))}
          </div>
        </>
      )}

      {/* Дни недели */}
      <div>
        <label className="block text-sm font-medium mb-1">Дни недели (опционально)</label>
        <DayOfWeekPicker value={form.daysOfWeek} onChange={(v) => onChange("daysOfWeek", v)} />
      </div>

      {/* Вкл/Выкл */}
      <label className="inline-flex items-center gap-2">
        <input
          type="checkbox"
          checked={form.isEnabled ?? true}
          onChange={(e) => onChange("isEnabled", e.target.checked)}
        />
        Включено
      </label>

      {/* Превью */}
      <div className="text-sm text-gray-700 border-t pt-3">{schedulePreview(form)}</div>

      {/* Кнопки */}
      <div className="flex gap-2">
        <button className="flex-1 bg-black text-white rounded-xl py-3">Сохранить</button>
        <button
          type="button"
          className="flex-1 bg-gray-100 rounded-xl py-3"
          onClick={() => nav(-1)}
        >
          Отмена
        </button>
      </div>
    </form>
  );
}