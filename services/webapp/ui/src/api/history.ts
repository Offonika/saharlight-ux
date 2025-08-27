import { http } from './http';

export interface HistoryRecord {
  id: string;
  date: string;
  time: string;
  sugar?: number;
  carbs?: number;
  breadUnits?: number;
  insulin?: number;
  notes?: string;
  type: 'measurement' | 'meal' | 'insulin';
}

export async function getHistory(): Promise<HistoryRecord[]> {
  try {
    const data = await http.get<unknown>('/history');
    if (!Array.isArray(data)) {
      throw new Error('Некорректный ответ');
    }
    return data as HistoryRecord[];
  } catch (error) {
    console.error('Failed to fetch history:', error);
    throw new Error('Не удалось загрузить историю');
  }
}

export async function updateRecord(record: HistoryRecord) {
  try {
    return await http.post('/history', record);
  } catch (error) {
    console.error('Failed to update history record:', error);
    throw new Error('Не удалось обновить запись');
  }
}

export async function deleteRecord(id: string) {
  try {
    return await http.delete(`/history/${id}`);
  } catch (error) {
    console.error('Failed to delete history record:', error);
    throw new Error('Не удалось удалить запись');
  }
}

