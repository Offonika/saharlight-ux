import type { ReminderSchema } from "@sdk";
import type { RemindersApi } from "@sdk/apis";
import type { Reminder } from "../types";

export async function bulkToggle(api: RemindersApi, items: Reminder[], enable: boolean) {
  let successCount = 0;
  let errorCount = 0;

  for (const r of items) {
    if (r.isEnabled !== enable) {
      try {
        const reminder: ReminderSchema = {
          telegramId: r.telegramId,
          id: r.id,
          type: r.type as ReminderSchema["type"],
          kind: r.kind,
          time: r.time ?? undefined,
          intervalMinutes: r.intervalMinutes ?? undefined,
          minutesAfter: r.minutesAfter ?? undefined,
          daysOfWeek: r.daysOfWeek ? new Set(r.daysOfWeek) : undefined,
          isEnabled: enable,
        };
        await api.remindersPatch({ reminder });
        successCount++;
      } catch {
        // Ignore individual errors, count them for summary
        errorCount++;
      }
    }
  }

  return { successCount, errorCount, totalChanged: successCount + errorCount };
}
