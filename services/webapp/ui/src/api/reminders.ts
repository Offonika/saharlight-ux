import { DefaultApi, Reminder } from '@sdk';

const api = new DefaultApi();

export async function getReminders(telegramId = 1): Promise<Reminder[]> {
  const data = await api.remindersGet({ telegramId });
  return Array.isArray(data) ? data : [data];
}

export async function createReminder(reminder: Reminder) {
  return api.remindersPost({ reminder });
}

export async function updateReminder(reminder: Reminder) {
  return api.remindersPatch({ reminder });
}

export async function deleteReminder(telegramId: number, id: number) {
  return api.remindersDelete({ telegramId, id });
}
