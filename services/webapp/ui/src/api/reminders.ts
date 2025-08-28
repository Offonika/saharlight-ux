
import type { ReminderSchema } from '@sdk';
import { http } from './http';
import { mockApi } from './mock-server';

// Определяем, находимся ли мы в режиме разработки
const isDevelopment = import.meta.env.DEV;

export async function getReminders(
  telegramId: number,
): Promise<ReminderSchema[]> {
  try {
    if (isDevelopment) {
      console.log('[API] Using mock server for getReminders');
      return await mockApi.getReminders(telegramId);
    }
    return await http.get<ReminderSchema[]>(
      `/reminders?telegramId=${telegramId}`,
    );
  } catch (error) {
    console.error('[API] Failed to fetch reminders:', error);
    throw new Error('Не удалось загрузить напоминания');
  }
}

export async function getReminder(
  telegramId: number,
  id: number,
): Promise<ReminderSchema> {
  try {
    if (isDevelopment) {
      console.log('[API] Using mock server for getReminder');
      return await mockApi.getReminder(telegramId, id);
    }
    return await http.get<ReminderSchema>(
      `/reminders/${id}?telegramId=${telegramId}`,
    );
  } catch (error) {
    console.error('Failed to fetch reminder:', error);
    throw new Error('Не удалось загрузить напоминание');
  }
}

export async function createReminder(reminder: ReminderSchema) {
  try {
    if (isDevelopment) {
      console.log('[API] Using mock server for createReminder');
      return await mockApi.createReminder(reminder);
    }
    return await http.post<ReminderSchema>('/reminders', reminder);
  } catch (error) {
    console.error('Failed to create reminder:', error);
    throw new Error('Не удалось создать напоминание');
  }
}

export async function updateReminder(reminder: ReminderSchema) {
  try {
    if (isDevelopment) {
      console.log('[API] Using mock server for updateReminder');
      return await mockApi.updateReminder(reminder);
    }
    return await http.patch<ReminderSchema>('/reminders', reminder);
  } catch (error) {
    console.error('Failed to update reminder:', error);
    throw new Error('Не удалось обновить напоминание');
  }
}

export async function deleteReminder(telegramId: number, id: number) {
  try {
    if (isDevelopment) {
      console.log('[API] Using mock server for deleteReminder');
      return await mockApi.deleteReminder(telegramId, id);
    }
    return await http.delete(`/reminders?telegramId=${telegramId}&id=${id}`);
  } catch (error) {
    console.error('Failed to delete reminder:', error);
    throw new Error('Не удалось удалить напоминание');
  }
}
