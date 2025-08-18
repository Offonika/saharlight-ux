import { describe, it, expect, vi, afterEach } from 'vitest';

const mockTgFetch = vi.hoisted(() => vi.fn());

vi.mock('../lib/tgFetch', () => ({ tgFetch: mockTgFetch }));

import { getHistory } from './history';

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
});
