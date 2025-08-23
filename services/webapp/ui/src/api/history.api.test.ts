import { describe, it, expect, vi, afterEach } from 'vitest';
import { Configuration } from '@offonika/diabetes-ts-sdk/runtime';

const mockHistoryGet = vi.hoisted(() => vi.fn());
const mockHistoryPost = vi.hoisted(() => vi.fn());
const mockHistoryIdDelete = vi.hoisted(() => vi.fn());

vi.mock('@offonika/diabetes-ts-sdk', () => ({
  HistoryApi: vi.fn(() => ({
    historyGet: mockHistoryGet,
    historyPost: mockHistoryPost,
    historyIdDelete: mockHistoryIdDelete,
  })),
  Configuration,
}));

import { getHistory, updateRecord, deleteRecord } from './history';

afterEach(() => {
  mockHistoryGet.mockReset();
  mockHistoryPost.mockReset();
  mockHistoryIdDelete.mockReset();
});

describe('getHistory', () => {
  it('returns parsed history on valid response', async () => {
    const history = [
      { id: '1', date: '2024-01-01', time: '12:00', type: 'meal' },
    ];
    mockHistoryGet.mockResolvedValueOnce(history);
    await expect(getHistory()).resolves.toEqual(history);
  });

  it('throws on invalid history item', async () => {
    mockHistoryGet.mockResolvedValueOnce([
      { id: '1', time: '12:00', type: 'meal' } as any,
    ]);
    await expect(getHistory()).rejects.toThrow(
      'Некорректная запись истории',
    );
  });

  it('forwards signal to API', async () => {
    const controller = new AbortController();
    mockHistoryGet.mockResolvedValueOnce([]);
    await getHistory(controller.signal);
    expect(mockHistoryGet).toHaveBeenCalledWith(
      {},
      { signal: controller.signal },
    );
  });
});

describe('updateRecord', () => {
  const record = {
    id: '1',
    date: '2024-01-01',
    time: '12:00',
    type: 'meal',
  };

  it('sends record to API and returns ok status', async () => {
    const ok = { status: 'ok' };
    mockHistoryPost.mockResolvedValueOnce(ok);
    await expect(updateRecord(record)).resolves.toEqual(ok);
    expect(mockHistoryPost).toHaveBeenCalledWith({ historyRecordSchemaInput: record });
  });

  it('throws on error status', async () => {
    mockHistoryPost.mockResolvedValueOnce({ status: 'error' });
    await expect(updateRecord(record)).rejects.toThrow(
      'Не удалось обновить запись',
    );
  });
});

describe('deleteRecord', () => {
  it('calls API with DELETE and returns ok status', async () => {
    const ok = { status: 'ok' };
    mockHistoryIdDelete.mockResolvedValueOnce(ok);
    await expect(deleteRecord('1')).resolves.toEqual(ok);
    expect(mockHistoryIdDelete).toHaveBeenCalledWith({ id: '1' });
  });

  it('throws on error status', async () => {
    mockHistoryIdDelete.mockResolvedValueOnce({ status: 'error' });
    await expect(deleteRecord('1')).rejects.toThrow(
      'Не удалось удалить запись',
    );
  });
});
