import { describe, it, expect, vi, afterEach } from 'vitest';

const mockTgFetch = vi.hoisted(() => vi.fn());

vi.mock('../lib/tgFetch', () => ({ tgFetch: mockTgFetch }));

import {
  fetchAnalytics,
  fetchDayStats,
  fallbackAnalytics,
  fallbackDayStats,
} from './stats';

afterEach(() => {
  mockTgFetch.mockReset();
});

describe('fetchAnalytics', () => {
  it('returns analytics on valid response', async () => {
    const analytics = [
      { date: '2024-02-01', sugar: 5.5 },
      { date: '2024-02-02', sugar: 6.1 },
    ];
    mockTgFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(analytics)),
    );
    await expect(fetchAnalytics(1)).resolves.toEqual(analytics);
  });

  it('returns fallback on invalid response', async () => {
    mockTgFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ foo: 'bar' })),
    );
    await expect(fetchAnalytics(1)).resolves.toBe(fallbackAnalytics);
  });

  it('returns fallback on network error', async () => {
    mockTgFetch.mockRejectedValueOnce(new Error('network'));
    await expect(fetchAnalytics(1)).resolves.toBe(fallbackAnalytics);
  });
});

describe('fetchDayStats', () => {
  it('returns stats on valid response', async () => {
    const stats = { sugar: 5.7, breadUnits: 3, insulin: 10 };
    mockTgFetch.mockResolvedValueOnce(new Response(JSON.stringify(stats)));
    await expect(fetchDayStats(1)).resolves.toEqual(stats);
  });

  it('returns fallback on invalid response', async () => {
    mockTgFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ sugar: 'bad' })),
    );
    await expect(fetchDayStats(1)).resolves.toBe(fallbackDayStats);
  });

  it('returns fallback on network error', async () => {
    mockTgFetch.mockRejectedValueOnce(new Error('network'));
    await expect(fetchDayStats(1)).resolves.toBe(fallbackDayStats);
  });
});

