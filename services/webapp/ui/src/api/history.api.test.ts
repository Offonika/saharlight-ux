import { describe, it, expect, vi, afterEach } from 'vitest';

const mockHistoryGet = vi.hoisted(() => vi.fn());
const mockHistoryPost = vi.hoisted(() => vi.fn());
const mockHistoryDelete = vi.hoisted(() => vi.fn());

vi.mock('@offonika/diabetes-ts-sdk', () => ({
  HistoryApi: vi.fn(() => ({
    historyGet: mockHistoryGet,
    historyPost: mockHistoryPost,
    historyDelete: mockHistoryDelete,
  })),
  Configuration: class {},
}));

import type { HistoryRecord } from './history';
import { getHistory, updateRecord, deleteRecord } from './history';

afterEach(() => {
  mockHistoryGet.mockReset();
  mockHistoryPost.mockReset();
  mockHistoryDelete.mockReset();
});

describe('getHistory', () => {
  it('returns history from API', async () => {
    const history = [{ id: '1', date: '2024-01-01', time: '12:00', type: 'meal' }];
    mockHistoryGet.mockResolvedValueOnce(history as any);
    await expect(getHistory()).resolves.toBe(history);
  });

  it('passes signal to API', async () => {
    const controller = new AbortController();
    mockHistoryGet.mockResolvedValueOnce([]);
    await getHistory(controller.signal);
    expect(mockHistoryGet).toHaveBeenCalledWith({}, { signal: controller.signal });
  });

  it('rethrows API errors', async () => {
    const err = new Error('fail');
    mockHistoryGet.mockRejectedValueOnce(err);
    await expect(getHistory()).rejects.toBe(err);
  });
});

describe('updateRecord', () => {
  const record: HistoryRecord = {
    id: '1',
    date: '2024-01-01',
    time: '12:00',
    type: 'meal',
  };

  it('sends record to API', async () => {
    const ok = { status: 'ok' } as any;
    mockHistoryPost.mockResolvedValueOnce(ok);
    await expect(updateRecord(record)).resolves.toBe(ok);
    expect(mockHistoryPost).toHaveBeenCalledWith({
      historyRecordSchemaInput: {
        ...record,
        date: new Date('2024-01-01'),
      },
    });
  });

  it('rethrows API errors', async () => {
    const err = new Error('api');
    mockHistoryPost.mockRejectedValueOnce(err);
    await expect(updateRecord(record)).rejects.toBe(err);
  });
});

describe('deleteRecord', () => {
  it('calls API delete', async () => {
    const ok = { status: 'ok' } as any;
    mockHistoryDelete.mockResolvedValueOnce(ok);
    await expect(deleteRecord('1')).resolves.toBe(ok);
    expect(mockHistoryDelete).toHaveBeenCalledWith({ recordId: '1' });
  });

  it('rethrows API errors', async () => {
    const err = new Error('api');
    mockHistoryDelete.mockRejectedValueOnce(err);
    await expect(deleteRecord('1')).rejects.toBe(err);
  });
});

