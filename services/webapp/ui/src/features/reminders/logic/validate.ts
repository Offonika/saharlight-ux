import type { ReminderDto } from "../types";

export type FormErrors = Partial<Record<keyof ReminderDto, string>>;

export function validate(v: ReminderDto): FormErrors {
  const e: FormErrors = {};
  
  if (v.kind === "at_time" && !/^([01]\d|2[0-3]):[0-5]\d$/.test(v.time || "")) {
    e.time = "Формат HH:MM";
  }
  
  if (v.kind === "every" && (!v.intervalMinutes || v.intervalMinutes < 1)) {
    e.intervalMinutes = "Минуты ≥ 1";
  }
  
  if (v.kind === "after_event") {
    const m = v.minutesAfter;
    if (m === undefined) {
      e.minutesAfter = "Укажите минуты";
    } else if (m < 5 || m > 480) {
      e.minutesAfter = "Минуты 5..480";
    } else if (m % 5 !== 0) {
      e.minutesAfter = "Кратно 5";
    }
  }
  
  return e;
}

export const hasErrors = (e: FormErrors) => Object.keys(e).length > 0;