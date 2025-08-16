import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

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
    const res = await tgFetch(`${API_BASE}/history`);
    if (!res.ok) {
      throw new Error('Не удалось загрузить историю');
    }
    const data = await res.json();
    if (!Array.isArray(data)) {
      throw new Error('Некорректный ответ');
    }
    return data as HistoryRecord[];
  } catch (error) {
    console.error('Failed to fetch history:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось загрузить историю');
  }
}

export async function updateRecord(record: HistoryRecord) {
  try {
    const res = await tgFetch(`${API_BASE}/history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.status !== 'ok') {
      throw new Error(data.detail || 'Не удалось обновить запись');
    }
    return data;
  } catch (error) {
    console.error('Failed to update history record:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось обновить запись');
  }
}

export async function deleteRecord(id: string) {
  try {
    const res = await tgFetch(`${API_BASE}/history/${encodeURIComponent(id)}`, { method: 'DELETE' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.status !== 'ok') {
      throw new Error(data.detail || 'Не удалось удалить запись');
    }
    return data;
  } catch (error) {
    console.error('Failed to delete history record:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось удалить запись');
  }
}

