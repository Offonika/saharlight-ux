import { z } from 'zod';
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

const historyRecordSchema = z.object({
  id: z.string(),
  date: z.string(),
  time: z.string(),
  sugar: z.number().optional(),
  carbs: z.number().optional(),
  breadUnits: z.number().optional(),
  insulin: z.number().optional(),
  notes: z.string().optional(),
  type: z.enum(['measurement', 'meal', 'insulin']),
});

export async function getHistory(): Promise<HistoryRecord[]> {
  try {
    const res = await tgFetch(`${API_BASE}/history`);
    const data = await res.json();
    if (!Array.isArray(data)) {
      throw new Error('Некорректный ответ API');
    }
    const parsed = z.array(historyRecordSchema).safeParse(data);
    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      const path = issue.path.join('.') || 'элемент';
      throw new Error(`Некорректная запись истории: ${path} ${issue.message}`);
    }
    return parsed.data as HistoryRecord[];
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
    if (data.status !== 'ok') {
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
    if (data.status !== 'ok') {
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

