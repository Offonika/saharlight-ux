import type { ReminderFormValues } from "../api/buildPayload";

export type FormErrors = Partial<Record<keyof ReminderFormValues, string>>;

export function validate(v: ReminderFormValues): FormErrors {
  const e: FormErrors = {};
  
  if (v.kind === "at_time" && !/^([01]\d|2[0-3]):[0-5]\d$/.test(v.time || "")) {
    e.time = "Формат HH:MM";
  }
  
  if (v.kind === "every" && (!v.intervalMinutes || v.intervalMinutes < 1)) {
    e.intervalMinutes = "Минуты ≥ 1";
  }
  
  if (v.kind === "after_event" && (!v.minutesAfter || v.minutesAfter < 1)) {
    e.minutesAfter = "Минуты ≥ 1";
  }
  
  return e;
}

export const hasErrors = (e: FormErrors) => Object.keys(e).length > 0;