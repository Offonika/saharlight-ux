import { describe, it, expect, vi, afterEach } from 'vitest';

const mockTgFetch = vi.hoisted(() => vi.fn());

vi.mock('../lib/tgFetch', () => ({ tgFetch: mockTgFetch }));

import { API_BASE } from './base';
import { getHistory, updateRecord, deleteRecord } from './history';

afterEach(() => {
  mockTgFetch.mockReset();
});

describe('getHistory', () => {
  it('returns parsed history on valid response', async () => {
    const history = [
      { id: '1', date: '2024-01-01', time: '12:00', type: 'meal' },
    ];
    mockTgFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(history)),
    );
    await expect(getHistory()).resolves.toEqual(history);
  });

  it('throws on invalid history item', async () => {
    mockTgFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify([{ id: '1', time: '12:00', type: 'meal' }]),
      ),
    );
    await expect(getHistory()).rejects.toThrow(
      'Некорректная запись истории',
    );
  });

  it('forwards signal to tgFetch', async () => {
    const controller = new AbortController();
    mockTgFetch.mockResolvedValueOnce(new Response(JSON.stringify([])));
    await getHistory(controller.signal);
    expect(mockTgFetch).toHaveBeenCalledWith(
      `${API_BASE}/history`,
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
    mockTgFetch.mockResolvedValueOnce(new Response(JSON.stringify(ok)));
    await expect(updateRecord(record)).resolves.toEqual(ok);
    expect(mockTgFetch).toHaveBeenCalledWith(
      `${API_BASE}/history`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(record),
      },
    );
  });

  it('throws on error status', async () => {
    mockTgFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'error' })),
    );
    await expect(updateRecord(record)).rejects.toThrow(
      'Не удалось обновить запись',
    );
  });
});

describe('deleteRecord', () => {
  it('calls API with DELETE and returns ok status', async () => {
    const ok = { status: 'ok' };
    mockTgFetch.mockResolvedValueOnce(new Response(JSON.stringify(ok)));
    await expect(deleteRecord('1')).resolves.toEqual(ok);
    expect(mockTgFetch).toHaveBeenCalledWith(
      `${API_BASE}/history/1`,
      { method: 'DELETE' },
    );
  });

  it('throws on error status', async () => {
    mockTgFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'error' })),
    );
    await expect(deleteRecord('1')).rejects.toThrow(
      'Не удалось удалить запись',
    );
  });
});
