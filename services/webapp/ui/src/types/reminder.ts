import { type NormalizedReminderType } from "@/lib/reminders";

export interface Reminder {
  id: number;
  type: NormalizedReminderType;
  title: string;
  time: string; // "HH:MM"
  active?: boolean;
  interval?: number; // stored in minutes
}

