import type { ReminderSchema } from "@sdk";

export async function bulkToggle(api: any, items: any[], enable: boolean) {
  let successCount = 0;
  let errorCount = 0;

  for (const r of items) {
    if (r.isEnabled !== enable) {
      try {
        const reminder: ReminderSchema = {
          telegramId: r.telegramId,
          id: r.id,
          type: r.type,
          kind: r.kind,
          time: r.time ?? undefined,
          intervalMinutes: r.intervalMinutes ?? undefined,
          minutesAfter: r.minutesAfter ?? undefined,
          daysOfWeek: r.daysOfWeek ?? undefined,
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
