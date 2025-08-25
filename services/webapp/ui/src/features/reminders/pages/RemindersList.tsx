import React, { useEffect, useMemo, useState } from "react";
import { useRemindersApi } from "../api/reminders";
import { formatNextAt } from "../../../shared/datetime";
import { useTelegram } from "@/hooks/useTelegram";

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
  if (r.kind === "after_event" && r.minutesAfter) return `через ${r.minutesAfter} мин (после события)`;
  return "";
}

export default function RemindersList() {
  const api = useRemindersApi();
  const { user } = useTelegram();
  const [items, setItems] = useState<ReminderDto[]>([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    if (!user?.id) return;
    setLoading(true);
    try {
      const res = await api.remindersGet({ telegramId: user.id });
      setItems(res as any);
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
      await api.remindersPatch({ telegramId: r.telegramId, id: r.id, isEnabled: !r.isEnabled });
      load();
    } catch {
      setItems(items);
      alert("Не удалось обновить статус");
    }
  }

  async function remove(r: ReminderDto) {
    if (!confirm("Удалить напоминание?")) return;
    const optimistic = items.filter(x => x.id !== r.id);
    setItems(optimistic);
    try {
      await api.remindersDelete({ telegramId: r.telegramId, id: r.id });
    } catch {
      alert("Не удалось удалить");
      setItems(items);
    }
  }

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-3">
        <h1 className="text-xl font-semibold">Напоминания</h1>
        <a href="/reminders/new" className="px-3 py-2 rounded-lg bg-black text-white">+ Добавить</a>
      </div>

      {loading && <div>Загрузка…</div>}

      {!loading && groups.map(([type, arr]) => (
        <div key={type} className="mb-5">
          <h2 className="text-sm uppercase text-gray-500 mb-2">{TYPE_LABEL[type] ?? "Другое"}</h2>
          <div className="space-y-2">
            {arr.map(r => (
              <div key={r.id} className="border rounded-xl p-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">{r.title || TYPE_LABEL[r.type] || "Напоминание"}</div>
                  <div className="text-sm text-gray-600">{scheduleLine(r)}</div>
                  <div className="text-xs text-gray-500">Следующее: {formatNextAt(r.nextAt)}</div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => toggleEnabled(r)} className={`px-3 py-1 rounded-lg border ${r.isEnabled ? "bg-black text-white border-black" : "border-gray-300"}`}>
                    {r.isEnabled ? "Вкл." : "Выкл."}
                  </button>
                  <a href={`/reminders/${r.id}/edit`} className="px-3 py-1 rounded-lg border border-gray-300">✏️</a>
                  <button onClick={() => remove(r)} className="px-3 py-1 rounded-lg border border-gray-300">🗑</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {!loading && !items.length && <div className="text-gray-600">Пока нет напоминаний.</div>}
    </div>
  );
}

