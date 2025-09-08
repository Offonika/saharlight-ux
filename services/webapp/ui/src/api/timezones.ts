import { api } from './index';

export async function getTimezones(): Promise<string[]> {
  try {
    const data = await api.get<unknown>('/timezones');
    if (Array.isArray(data)) {
      return data as string[];
    }
    throw new Error('Некорректный ответ сервера');
  } catch (error) {
    console.error('Failed to load timezones:', error);
    if (error instanceof Error) {
      throw new Error(
        `Не удалось получить список часовых поясов: ${error.message}`,
      );
    }
    throw error;
  }
}
