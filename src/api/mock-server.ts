
// Mock server для тестирования в режиме разработки
let mockReminders: any[] = [];
let nextId = 1;

export const mockApi = {
  async getReminders(telegramId: number) {
    console.log('[MockAPI] Getting reminders for telegram ID:', telegramId);
    console.log('[MockAPI] All reminders:', mockReminders);
    const filtered = mockReminders.filter(r => r.telegramId === telegramId);
    console.log('[MockAPI] Filtered reminders:', filtered);
    return filtered;
  },

  async createReminder(reminder: any) {
    console.log('[MockAPI] Creating reminder:', reminder);
    const newReminder = {
      id: nextId++,
      telegramId: reminder.telegram_id,
      type: reminder.type,
      title: reminder.title || null,
      kind: "at_time" as const,
      time: reminder.time,
      intervalMinutes: reminder.interval_minutes || null,
      minutesAfter: reminder.minutes_after || null,
      daysOfWeek: reminder.days_of_week || null,
      isEnabled: reminder.is_enabled,
      nextAt: reminder.next_at || null,
    };
    mockReminders.push(newReminder);
    return { id: newReminder.id, status: 'ok' };
  },

  async updateReminder(reminder: any) {
    console.log('[MockAPI] Updating reminder:', reminder);
    const index = mockReminders.findIndex(r => r.id === reminder.id);
    if (index >= 0) {
      mockReminders[index] = reminder;
    }
    return { id: reminder.id, status: 'ok' };
  },

  async deleteReminder(telegramId: number, id: number) {
    console.log('[MockAPI] Deleting reminder:', id);
    mockReminders = mockReminders.filter(r => !(r.id === id && r.telegramId === telegramId));
    return { status: 'ok' };
  },

  async getReminder(telegramId: number, id: number) {
    console.log('[MockAPI] Getting single reminder:', id);
    return mockReminders.find(r => r.id === id && r.telegramId === telegramId) || null;
  }
};
