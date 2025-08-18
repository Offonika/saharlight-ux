import { DefaultApi, instanceOfReminder, type Reminder } from '@sdk';
import { Configuration } from '@sdk/runtime';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

const api = new DefaultApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export async function getReminders(telegramId: number): Promise<Reminder[]> {
  try {
    const data = await api.remindersGet({ telegramId });

    if (!data) {
      return [];
    }

    if (!Array.isArray(data)) {
      console.error('Unexpected reminders API response:', data);
      return [];
    }

    return data;
  } catch (error) {
    console.error('Failed to fetch reminders:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось загрузить напоминания');
  }
}

export async function getReminder(
  telegramId: number,
  id: number,
): Promise<Reminder> {
  try {
    const data = await api.remindersGet({ telegramId, id });

    if (!data || Array.isArray(data) || !instanceOfReminder(data)) {
      console.error('Unexpected reminder API response:', data);
      throw new Error('Некорректный ответ API');
    }

    return data;
  } catch (error) {
    console.error('Failed to fetch reminder:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось загрузить напоминание');
  }
}

export async function createReminder(reminder: Reminder) {
  try {
    return await api.remindersPost({ reminder });
  } catch (error) {
    console.error('Failed to create reminder:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось создать напоминание');
  }
}

export async function updateReminder(reminder: Reminder) {
  try {
    return await api.remindersPost({ reminder });
  } catch (error) {
    console.error('Failed to update reminder:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось обновить напоминание');
  }
}

export async function deleteReminder(telegramId: number, id: number) {
  try {
    const reminder = await getReminder(telegramId, id);
    return await updateReminder({ ...reminder, isEnabled: false });
  } catch (error) {
    console.error('Failed to delete reminder:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось удалить напоминание');
  }
}
