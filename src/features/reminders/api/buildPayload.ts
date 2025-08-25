export type ReminderType =
  | "sugar" | "insulin_short" | "insulin_long" | "after_meal"
  | "meal" | "sensor_change" | "injection_site" | "custom";
export type ScheduleKind = "at_time" | "every" | "after_event";

export interface ReminderFormValues {
  telegramId: number;
  type: ReminderType;
  kind: ScheduleKind;
  time?: string;
  intervalMinutes?: number;
  minutesAfter?: number;
  daysOfWeek?: number[];
  title?: string;
  isEnabled?: boolean;
}

const TYPE_LABEL: Record<ReminderType, string> = {
  sugar: "Измерение сахара",
  insulin_short: "Инсулин (короткий)",
  insulin_long: "Инсулин (длинный)",
  after_meal: "После еды",
  meal: "Приём пищи",
  sensor_change: "Смена сенсора",
  injection_site: "Смена места инъекции",
  custom: "Напоминание",
};

function generateTitle(v: ReminderFormValues): string {
  if (v.title?.trim()) return v.title.trim();
  if (v.kind === "at_time" && v.time) return `${TYPE_LABEL[v.type]} · ${v.time}`;
  if (v.kind === "every" && v.intervalMinutes) return `${TYPE_LABEL[v.type]} · каждые ${v.intervalMinutes} мин`;
  if (v.kind === "after_event" && v.minutesAfter) return `${TYPE_LABEL[v.type]} · через ${v.minutesAfter} мин`;
  return TYPE_LABEL[v.type];
}

export function buildReminderPayload(v: ReminderFormValues) {
  const base = {
    telegramId: v.telegramId,
    type: v.type,
    kind: v.kind,
    daysOfWeek: v.daysOfWeek?.length ? v.daysOfWeek : undefined,
    isEnabled: v.isEnabled ?? true,
  };
  const schedule =
    v.kind === "at_time" ? { time: v.time } :
    v.kind === "every"    ? { intervalMinutes: v.intervalMinutes } :
                            { minutesAfter: v.minutesAfter };

  return { ...base, ...schedule, title: generateTitle(v) };
}