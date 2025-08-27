export async function bulkToggle(api: any, items: any[], enable: boolean) {
  let successCount = 0;
  let errorCount = 0;
  
  for (const r of items) {
    if (r.isEnabled !== enable) {
      try {
        await api.remindersPatch({
          id: r.id,
          telegramId: r.telegramId,
          isEnabled: enable,
        });
        successCount++;
      } catch {
        // Ignore individual errors, count them for summary
        errorCount++;
      }
    }
  }
  
  return { successCount, errorCount, totalChanged: successCount + errorCount };
}