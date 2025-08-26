import { describe, it, expect, vi, afterEach, beforeAll } from 'vitest';

const mockGetAnalytics = vi.hoisted(() => vi.fn());
const mockGetStats = vi.hoisted(() => vi.fn());

vi.mock(
  '@sdk/runtime',
  () => {
    class Configuration {}
    class ResponseError extends Error {
      constructor(public response: { status: number }) {
        super('Response error');
      }
    }
    return { Configuration, ResponseError };
  },
  { virtual: true },
);

vi.mock(
  '@sdk',
  () => ({
    DefaultApi: vi.fn(() => ({
      getAnalyticsAnalyticsGet: mockGetAnalytics,
      getStatsStatsGet: mockGetStats,
    })),
  }),
  { virtual: true },
);

import {
  fetchAnalytics,
  fetchDayStats,
  getFallbackAnalytics,
  getFallbackDayStats,
  type DayStats,
} from './stats';

let ResponseError: new (arg: { status: number }) => Error;

beforeAll(async () => {
  ({ ResponseError } = await import('@sdk/runtime'));
});

afterEach(() => {
  mockGetAnalytics.mockReset();
  mockGetStats.mockReset();
});

describe('fetchAnalytics', () => {
  it('returns analytics on valid response', async () => {
    const analytics = [
      { date: '2024-02-01', sugar: 5.5 },
      { date: '2024-02-02', sugar: 6.1 },
    ];
    mockGetAnalytics.mockResolvedValueOnce(analytics);
    await expect(fetchAnalytics(1)).resolves.toEqual(analytics);
    expect(mockGetAnalytics).toHaveBeenCalledWith({ telegramId: 1 });
  });

  it('returns fallback on invalid response', async () => {
    mockGetAnalytics.mockResolvedValueOnce({ foo: 'bar' });
    await expect(fetchAnalytics(1)).resolves.toEqual(getFallbackAnalytics());
  });

  it('generates recent fallback on network error', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-05-05'));
    mockGetAnalytics.mockRejectedValueOnce(new Error('network'));
    await expect(fetchAnalytics(1)).resolves.toEqual(getFallbackAnalytics());
    const result = getFallbackAnalytics();
    expect(result[0].date).toBe('2024-05-01');
    expect(result[4].date).toBe('2024-05-05');
    vi.useRealTimers();
  });

  it('returns fallback on 403 response', async () => {
    mockGetAnalytics.mockRejectedValueOnce(
      new ResponseError({ status: 403 }),
    );
    await expect(fetchAnalytics(1)).resolves.toEqual(getFallbackAnalytics());
  });
});

describe('fetchDayStats', () => {
  it('returns stats on valid response', async () => {
    const stats = { sugar: 5.7, breadUnits: 3, insulin: 10 };
    mockGetStats.mockResolvedValueOnce(stats);
    await expect(fetchDayStats(1)).resolves.toEqual(stats);
    expect(mockGetStats).toHaveBeenCalledWith({ telegramId: 1 });
  });

  it('returns fallback on invalid response', async () => {
    mockGetStats.mockResolvedValueOnce({ sugar: 'bad' } as unknown as DayStats);
    await expect(fetchDayStats(1)).resolves.toEqual(getFallbackDayStats());
  });

  it('returns fallback on null response without logging', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetStats.mockResolvedValueOnce(null);
    await expect(fetchDayStats(1)).resolves.toEqual(getFallbackDayStats());
    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });

  it('returns fallback on network error', async () => {
    mockGetStats.mockRejectedValueOnce(new Error('network'));
    await expect(fetchDayStats(1)).resolves.toEqual(getFallbackDayStats());
  });

  it('returns fallback on 403 response', async () => {
    mockGetStats.mockRejectedValueOnce(new ResponseError({ status: 403 }));
    await expect(fetchDayStats(1)).resolves.toEqual(getFallbackDayStats());
  });
});

