import { z } from 'zod';
import { HistoryApi } from '@sdk';
import { Configuration } from '@sdk/runtime';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

const formatTime = (t: string) => t.slice(0, 5);

const historyRecordSchema = z.object({
  id: z.string(),
  date: z.string().transform((val, ctx) => {
    const parsed = new Date(val);
    if (isNaN(parsed.getTime())) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'Invalid date' });
    }
    return parsed;
  }),
  time: z.string().transform(formatTime),
  sugar: z.number().optional(),
  carbs: z.number().optional(),
  breadUnits: z.number().optional(),
  insulin: z.number().optional(),
  notes: z.string().optional(),
  type: z.enum(['measurement', 'meal', 'insulin']),
});

export type HistoryRecord = z.infer<typeof historyRecordSchema>;

const api = new HistoryApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export async function getHistory(signal?: AbortSignal): Promise<HistoryRecord[]> {
  try {
    const data = await api.historyGet({}, { signal });
    if (!Array.isArray(data)) {
      throw new Error('Некорректный ответ API');
    }
    const parsed = z.array(historyRecordSchema).safeParse(data);
    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      const path = issue.path.join('.') || 'элемент';
      throw new Error(`Некорректная запись истории: ${path} ${issue.message}`);
    }
    return parsed.data;
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
    const data = await api.historyPost({
      historyRecordSchemaInput: {
        ...record,
        date: new Date(record.date),
        time: formatTime(record.time),
      },
    });
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
    const data = await api.historyIdDelete({ id });
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

