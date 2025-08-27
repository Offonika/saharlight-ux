
import { RemindersApi, Configuration, ResponseError } from '@sdk';

import {
  instanceOfReminderSchema as instanceOfReminder,
  type ReminderSchema as Reminder,
} from '@sdk/models';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

const api = new RemindersApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export async function getReminders(
  telegramId: number,
  signal?: AbortSignal,
): Promise<Reminder[]> {
  try {
    const data = await api.remindersGet({ telegramId }, { signal });

    if (!data) {
      return [];
    }

    for (const reminder of data) {
      if (!instanceOfReminder(reminder)) {
        console.error('Unexpected reminder API response:', reminder);
        throw new Error('Некорректный ответ API');
      }
    }

    return data;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    console.error('Failed to fetch reminders:', error);
    if (error instanceof ResponseError && error.response.status === 404) {
      return [];
    }
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось загрузить напоминания');
  }
}

export async function getReminder(
  telegramId: number,
  id: number,
  signal?: AbortSignal,
): Promise<Reminder | null> {
  try {
    const data = await api.remindersIdGet({ telegramId, id }, { signal });

    if (!data || !instanceOfReminder(data)) {
      console.error('Unexpected reminder API response:', data);
      throw new Error('Некорректный ответ API');
    }

    return data;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    console.error('Failed to fetch reminder:', error);
    if (error instanceof ResponseError && error.response.status === 404) {
      return null;
    }
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
    return await api.remindersPatch({ reminder });
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
    return await api.remindersDelete({ telegramId, id });
  } catch (error) {
    console.error('Failed to delete reminder:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось удалить напоминание');
  }
}

export async function snoozeReminder(
  telegramId: number,
  id: number,
  minutes: number,
) {
  try {
    const url = `${API_BASE}/reminders/snooze?telegramId=${telegramId}&id=${id}&snooze=${minutes}`;
    const response = await tgFetch(url, { method: 'POST' });
    return await response.json();
  } catch (error) {
    console.error('Failed to snooze reminder:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось отложить напоминание');
  }
}
