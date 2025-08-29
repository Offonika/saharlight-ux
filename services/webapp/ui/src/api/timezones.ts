import { http } from './http';

export async function getTimezones(): Promise<string[]> {
  try {
    return await http.get<string[]>('/timezones');
  } catch (error) {
    console.warn('Failed to load timezones:', error);
    return [];
  }
}

