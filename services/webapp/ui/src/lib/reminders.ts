export type NormalizedReminderType = "sugar" | "insulin" | "meal" | "medicine";
export type ReminderType = NormalizedReminderType | "meds";

export const normalizeReminderType = (
  t: ReminderType,
): NormalizedReminderType => (t === "meds" ? "medicine" : t);
