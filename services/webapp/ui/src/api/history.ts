import { HistoryApi, Configuration } from '@offonika/diabetes-ts-sdk';
import type {
  HistoryRecordSchemaInput,
  HistoryRecordSchemaOutput,
} from '@offonika/diabetes-ts-sdk/models';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

export type HistoryRecord = HistoryRecordSchemaOutput;

const api = new HistoryApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

function toInput(record: HistoryRecord): HistoryRecordSchemaInput {
  const { date, ...rest } = record;
  return { ...rest, date: new Date(date) };
}

export async function getHistory(
  signal?: AbortSignal,
): Promise<HistoryRecord[]> {
  try {
    return await api.historyGet({}, { signal });
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
    return await api.historyPost({ historyRecordSchemaInput: toInput(record) });
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
    return await api.historyDelete({ recordId: id });
  } catch (error) {
    console.error('Failed to delete history record:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось удалить запись');
  }
}

