import { Reminder } from '@sdk';
import { http } from './http';

export async function getReminders(telegramId: number): Promise<Reminder[]> {
  try {
    return await http.get<Reminder[]>(`/reminders?telegram_id=${telegramId}`);
  } catch (error) {
    console.error('[API] Failed to fetch reminders:', error);
    throw new Error('Не удалось загрузить напоминания');
  }
}

export async function getReminder(
  telegramId: number,
  id: number,
): Promise<Reminder | null> {
  try {
    const data = await http.get<Reminder | Reminder[]>(
      `/reminders?telegram_id=${telegramId}&id=${id}`,
    );
    return Array.isArray(data) ? data[0] ?? null : data ?? null;
  } catch (error) {
    console.error('Failed to fetch reminder:', error);
    throw new Error('Не удалось загрузить напоминание');
  }
}

export async function createReminder(reminder: Reminder) {
  try {
    return await http.post<Reminder>('/reminders', { reminder });
  } catch (error) {
    console.error('Failed to create reminder:', error);
    throw new Error('Не удалось создать напоминание');
  }
}

export async function updateReminder(reminder: Reminder) {
  try {
    return await http.patch<Reminder>('/reminders', { reminder });
  } catch (error) {
    console.error('Failed to update reminder:', error);
    throw new Error('Не удалось обновить напоминание');
  }
}

export async function deleteReminder(telegramId: number, id: number) {
  try {
    return await http.delete(`/reminders/${id}?telegram_id=${telegramId}`);
  } catch (error) {
    console.error('Failed to delete reminder:', error);
    throw new Error('Не удалось удалить напоминание');
  }
}
