import { DefaultApi, Reminder } from '@sdk';

const api = new DefaultApi();

export async function getReminders(telegramId: number): Promise<Reminder[]> {
  const data = await api.remindersGet({ telegramId });
  return Array.isArray(data) ? data : [data];
}

export async function getReminder(
  telegramId: number,
  id: number,
): Promise<Reminder | null> {
  const data = await api.remindersGet({ telegramId, id });
  if (Array.isArray(data)) {
    return data[0] ?? null;
  }
  return data ?? null;
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
