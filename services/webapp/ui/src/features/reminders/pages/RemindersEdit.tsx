import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useRemindersApi } from "../api/reminders";
import { DayOfWeekPicker } from "../components/DayOfWeekPicker";
import { buildReminderPayload, type ReminderFormValues, type ScheduleKind, type ReminderType } from "../api/buildPayload";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";
import { mockApi } from "../../../api/mock-server";

// --- utils: достаём telegramId из initData
function getTelegramUserId(initData: string): number {
  try {
    const raw = new URLSearchParams(initData).get("user");
    if (!raw) return 0;
    const u = JSON.parse(decodeURIComponent(raw));
    return Number(u?.id ?? 0);
  } catch { return 0; }
}

export default function RemindersEdit() {
  const { id } = useParams();
  const api = useRemindersApi();
  const initData = useTelegramInitData();
  const telegramId = useMemo(() => getTelegramUserId(initData), [initData]);
  const nav = useNavigate();

  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<ReminderFormValues | null>(null);

  const onChange = <K extends keyof ReminderFormValues>(k: K, v: ReminderFormValues[K]) =>
    setForm((s) => (s ? { ...s, [k]: v } : s));

  const switchKind = (k: ScheduleKind) =>
    setForm((s) => (s ? {
      ...s, kind: k,
      time: k==="at_time" ? (s.time ?? "07:30") : undefined,
      intervalMinutes: k==="every" ? (s.intervalMinutes ?? 60) : undefined,
      minutesAfter: k==="after_event" ? (s.minutesAfter ?? 120) : undefined,
      type: k==="after_event" ? "after_meal" : s.type,
    } : s));

  useEffect(() => {
    (async () => {
      try {
        let dto: any = null;
        try {
          const response = await api.remindersGet({ telegramId, id: Number(id) });
          dto = Array.isArray(response) ? response[0] : response;
        } catch (apiError) {
          console.warn("Backend API failed, using mock API:", apiError);
          dto = await mockApi.getReminder(telegramId, Number(id));
        }
        
        if (!dto) {
          alert("Напоминание не найдено");
          nav("/reminders");
          return;
        }

        // определяем kind на основе данных
        let kind: ScheduleKind = "at_time";
        if (dto.time) kind = "at_time";
        else if (dto.intervalMinutes || dto.intervalHours) kind = "every";
        else if (dto.minutesAfter) kind = "after_event";

        // маппинг API → форма
        const fv: ReminderFormValues = {
          telegramId,
          type: kind === "after_event" ? "after_meal" : (dto.type as ReminderType),
          kind,
          time: dto.time ?? undefined,
          intervalMinutes: dto.intervalMinutes ?? (dto.intervalHours ? dto.intervalHours * 60 : undefined),
          minutesAfter: dto.minutesAfter ?? undefined,
          daysOfWeek: dto.daysOfWeek ?? undefined,
          title: dto.title ?? undefined,
          isEnabled: dto.isEnabled ?? true,
        };
        setForm(fv);
      } catch (err) {
        console.error("Failed to load reminder:", err);
        alert("Не удалось загрузить напоминание");
        nav("/reminders");
      } finally {
        setLoading(false);
      }
    })();
  }, [id, telegramId, api, nav]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    try {
      const payload = { id: Number(id), ...buildReminderPayload(form) };
      try {
        await api.remindersPatch({ reminder: payload as any });
      } catch (apiError) {
        console.warn("Backend API failed, using mock API:", apiError);
        await mockApi.updateReminder(payload);
      }
      nav("/reminders");
    } catch (err: any) {
      const text = await err?.response?.text?.();
      console.error("PATCH /reminders failed", err?.response?.status, text);
      alert("Не удалось сохранить изменения.");
    }
  }

  async function onDelete() {
    if (!confirm("Удалить напоминание?")) return;
    try {
      try {
        await api.remindersDelete({ telegramId, id: Number(id) });
      } catch (apiError) {
        console.warn("Backend API failed, using mock API:", apiError);
        await mockApi.deleteReminder(telegramId, Number(id));
      }
      nav("/reminders");
    } catch (err) {
      alert("Удаление не удалось");
    }
  }

  if (loading || !form) return <div className="p-4">Загрузка…</div>;

  const presetsTime = ["07:30","12:30","22:00"];
  const presetsEvery = [60,120,180,1440];
  const presetsAfter = [90,120,150];

  return (
    <form className="max-w-xl mx-auto p-4 space-y-4" onSubmit={onSave}>
      <div className="flex items-center justify-between">
        <button type="button" onClick={() => nav("/reminders")} className="px-3 py-2 rounded-lg border border-gray-300">← Назад</button>
        <h1 className="text-xl font-semibold">Редактировать напоминание</h1>
        <button type="button" onClick={onDelete} className="px-3 py-2 rounded-lg border border-gray-300">🗑 Удалить</button>
      </div>

      {/* Тип */}
      <label className="block text-sm font-medium">Тип</label>
      <select
        className="w-full border rounded-lg px-3 py-2"
        value={form.kind === "after_event" ? "after_meal" : form.type}
        onChange={(e) => onChange("type", e.target.value as ReminderType)}
        disabled={form.kind === "after_event"}
      >
        {["sugar","insulin_short","insulin_long","after_meal","meal","sensor_change","injection_site","custom"].map(v =>
          <option key={v} value={v}>{v}</option>
        )}
      </select>
      {form.kind === "after_event" && (
        <p className="text-xs text-gray-500 mt-1">
          Это напоминание сработает <b>после записи приёма пищи</b> в разделе «История».
        </p>
      )}

      {/* Режим */}
      <label className="block text-sm font-medium">Режим</label>
      <div className="flex gap-2">
        {[
          {value:"at_time",label:"Время"},
          {value:"every",label:"Каждые…"},
          {value:"after_event",label:"После события"},
        ].map(o => (
          <button key={o.value} type="button"
            onClick={() => switchKind(o.value as ScheduleKind)}
            className={`px-3 py-1 rounded-2xl border ${form.kind===o.value?"bg-black text-white border-black":"border-gray-300"}`}>
            {o.label}
          </button>
        ))}
      </div>

      {/* Поля по kind */}
      {form.kind==="at_time" && (
        <>
          <label className="block text-sm font-medium">Время (HH:MM)</label>
          <input type="time" className="w-full border rounded-lg px-3 py-2"
            value={form.time || ""} onChange={(e)=>onChange("time", e.target.value)} />
          <div className="flex gap-2">
            {presetsTime.map(t => <button key={t} type="button" className="px-3 py-1 rounded-2xl border border-gray-300" onClick={()=>onChange("time", t)}>{t}</button>)}
          </div>
        </>
      )}

      {form.kind==="every" && (
        <>
          <label className="block text-sm font-medium">Интервал (мин)</label>
          <input type="number" min={1} className="w-full border rounded-lg px-3 py-2"
            value={form.intervalMinutes ?? ""} onChange={(e)=>onChange("intervalMinutes", Number(e.target.value||0))} />
          <div className="flex gap-2">
            {presetsEvery.map(m => <button key={m} type="button" className="px-3 py-1 rounded-2xl border border-gray-300" onClick={()=>onChange("intervalMinutes", m)}>{m} мин</button>)}
          </div>
        </>
      )}

      {form.kind==="after_event" && (
        <>
          <label className="block text-sm font-medium">Задержка после еды (мин)</label>
          <input type="number" min={1} className="w-full border rounded-lg px-3 py-2"
            value={form.minutesAfter ?? ""} onChange={(e)=>onChange("minutesAfter", Number(e.target.value||0))} />
          <div className="flex gap-2">
            {presetsAfter.map(m => <button key={m} type="button" className="px-3 py-1 rounded-2xl border border-gray-300" onClick={()=>onChange("minutesAfter", m)}>{m} мин</button>)}
          </div>
        </>
      )}

      {/* Дни недели */}
      <div>
        <label className="block text-sm font-medium mb-1">Дни недели (опционально)</label>
        <DayOfWeekPicker value={form.daysOfWeek} onChange={(v)=>onChange("daysOfWeek", v)} />
      </div>

      {/* Название */}
      <label className="block text-sm font-medium">Название</label>
      <input className="w-full border rounded-lg px-3 py-2"
        value={form.title ?? ""} onChange={(e)=>onChange("title", e.target.value)} />

      {/* Вкл/Выкл */}
      <label className="inline-flex items-center gap-2">
        <input type="checkbox" checked={form.isEnabled ?? true}
          onChange={(e)=>onChange("isEnabled", e.target.checked)} />
        Включено
      </label>

      <button className="w-full bg-black text-white rounded-xl py-3">Сохранить</button>
    </form>
  );
}