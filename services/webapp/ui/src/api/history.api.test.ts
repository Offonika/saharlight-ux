import { describe, it, expect, vi, afterEach } from 'vitest';

const mockHistoryGet = vi.hoisted(() => vi.fn());
const mockHistoryPost = vi.hoisted(() => vi.fn());
const mockHistoryIdDelete = vi.hoisted(() => vi.fn());

vi.mock(
  '@sdk',
  () => ({
    HistoryApi: vi.fn(() => ({
      historyGet: mockHistoryGet,
      historyPost: mockHistoryPost,
      historyIdDelete: mockHistoryIdDelete,
    })),
    Configuration: class {},
  }),
  { virtual: true },
);

import { Configuration } from '@sdk';

import { getHistory, updateRecord, deleteRecord } from './history';

afterEach(() => {
  mockHistoryGet.mockReset();
  mockHistoryPost.mockReset();
  mockHistoryIdDelete.mockReset();
});

describe('getHistory', () => {
  it('returns parsed history on valid response', async () => {
    const apiResponse = [
      { id: '1', date: '2024-01-01', time: '12:00:30', type: 'meal' },
    ];
    mockHistoryGet.mockResolvedValueOnce(apiResponse);
    await expect(getHistory()).resolves.toEqual([
      { id: '1', date: new Date('2024-01-01'), time: '12:00', type: 'meal' },
    ]);
  });

  it('throws on invalid history item', async () => {
    mockHistoryGet.mockResolvedValueOnce([
      { id: '1', time: '12:00', type: 'meal' } as unknown,
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
    date: new Date('2024-01-01'),
    time: '12:00:30',
    type: 'meal',
  };

  it('sends record to API and returns ok status', async () => {
    const ok = { status: 'ok' };
    mockHistoryPost.mockResolvedValueOnce(ok);
    await expect(updateRecord(record)).resolves.toEqual(ok);
    expect(mockHistoryPost).toHaveBeenCalledWith({
      historyRecordSchemaInput: {
        id: '1',
        date: new Date('2024-01-01'),
        time: '12:00',
        type: 'meal',
      },
    });
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

describe('HistoryApi serialization', () => {
  it('sends ISO date strings', async () => {
    const fetchMock = vi.fn(async () => new Response('{}'));
    const { HistoryApi, Configuration } = await vi.importActual<
      typeof import('@sdk')
    >('@sdk');

    const api = new HistoryApi(
      new Configuration({ basePath: '', fetchApi: fetchMock }),
    );

    await api.historyPost({
      historyRecordSchemaInput: {
        id: '1',
        date: new Date('2024-01-01'),
        time: '12:00',
        type: 'meal',
      },
    });

    const body = JSON.parse(fetchMock.mock.calls[0][1]!.body as string);
    expect(body.date).toBe('2024-01-01');
  });
});
