export type ReminderType =
  | "sugar"
  | "insulin_short"
  | "insulin_long"
  | "after_meal"
  | "meal"
  | "sensor_change"
  | "injection_site"
  | "custom";

export type ScheduleKind = "at_time" | "every" | "after_event";

export interface ReminderDto {
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

export interface Reminder extends ReminderDto {
  id: number;
  isEnabled: boolean;
  nextAt?: string | null;
  lastFiredAt?: string | null;
  fires7d?: number;
}

