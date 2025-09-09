import { Configuration } from '@sdk/runtime.ts';
import { HistoryApi } from '@sdk/apis';
import type { HistoryRecordSchemaInput, HistoryRecordSchemaOutput } from '@sdk/models';
import { buildHeaders } from './http';

function makeApi(): HistoryApi {
  const hdrs = buildHeaders({ headers: {} }, true);
  const cfg = new Configuration({
    basePath: '/api',
    headers: Object.fromEntries(hdrs.entries()),
  });
  return new HistoryApi(cfg);
}

export async function getHistory(): Promise<(HistoryRecordSchemaOutput & { date: Date })[]> {
  try {
    const api = makeApi();
    const data = await api.historyGet();
    return data.map(r => ({ ...r, date: new Date(r.date) }));
  } catch (error) {
    console.error('Failed to fetch history:', error);
    throw new Error('Не удалось загрузить историю');
  }
}

export async function updateRecord(record: HistoryRecordSchemaInput): Promise<void> {
  try {
    const api = makeApi();
    await api.historyPost({
      historyRecordSchemaInput: {
        ...record,
        date: record.date instanceof Date ? record.date : new Date(record.date),
      },
    });
  } catch (error) {
    console.error('Failed to update history record:', error);
    throw new Error('Не удалось обновить запись');
  }
}

export async function deleteRecord(id: string): Promise<void> {
  try {
    const api = makeApi();
    await api.historyIdDelete({ id });
  } catch (error) {
    console.error('Failed to delete history record:', error);
    throw new Error('Не удалось удалить запись');
  }
}
