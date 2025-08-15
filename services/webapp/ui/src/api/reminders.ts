import { DefaultApi, Reminder } from '@sdk';
import { Configuration } from '@sdk/runtime';

const api = new DefaultApi(
  new Configuration({ basePath: import.meta.env.VITE_API_BASE }),
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
    throw new Error('Не удалось загрузить напоминания');
  }
}

export async function getReminder(
  telegramId: number,
  id: number,
): Promise<Reminder | null> {
  try {
    const data = await api.remindersGet({ telegramId, id });
    if (Array.isArray(data)) {
      return data[0] ?? null;
    }
    return data ?? null;
  } catch (error) {
    console.error('Failed to fetch reminder:', error);
    throw new Error('Не удалось загрузить напоминание');
  }
}

export async function createReminder(reminder: Reminder) {
  try {
    return await api.remindersPost({ reminder });
  } catch (error) {
    console.error('Failed to create reminder:', error);
    throw new Error('Не удалось создать напоминание');
  }
}

export async function updateReminder(reminder: Reminder) {
  try {
    return await api.remindersPatch({ reminder });
  } catch (error) {
    console.error('Failed to update reminder:', error);
    throw new Error('Не удалось обновить напоминание');
  }
}

export async function deleteReminder(telegramId: number, id: number) {
  try {
    return await api.remindersDelete({ telegramId, id });
  } catch (error) {
    console.error('Failed to delete reminder:', error);
    throw new Error('Не удалось удалить напоминание');
  }
}
