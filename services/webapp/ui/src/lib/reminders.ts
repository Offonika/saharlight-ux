export type NormalizedReminderType = "sugar" | "insulin" | "meal" | "medicine";
export type ReminderType = NormalizedReminderType | "meds";

export const normalizeReminderType = (
  t?: string,
): NormalizedReminderType => {
  switch (t) {
    case "sugar":
    case "insulin":
    case "meal":
    case "medicine":
      return t;
    case "meds":
      return "medicine";
    default:
      return "medicine";
  }
};
