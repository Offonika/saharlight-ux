import { describe, it, expect, vi, afterEach } from 'vitest';
import { Configuration } from '@offonika/diabetes-ts-sdk/runtime';

const mockGetAnalytics = vi.hoisted(() => vi.fn());
const mockGetStats = vi.hoisted(() => vi.fn());

vi.mock('@offonika/diabetes-ts-sdk', () => ({
  DefaultApi: vi.fn(() => ({
    getAnalyticsAnalyticsGet: mockGetAnalytics,
    getStatsStatsGet: mockGetStats,
  })),
  Configuration,
}));

import {
  fetchAnalytics,
  fetchDayStats,
  fallbackAnalytics,
  fallbackDayStats,
} from './stats';

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
    await expect(fetchAnalytics(1)).resolves.toBe(fallbackAnalytics);
  });

  it('returns fallback on network error', async () => {
    mockGetAnalytics.mockRejectedValueOnce(new Error('network'));
    await expect(fetchAnalytics(1)).resolves.toBe(fallbackAnalytics);
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
    mockGetStats.mockResolvedValueOnce({ sugar: 'bad' } as any);
    await expect(fetchDayStats(1)).resolves.toBe(fallbackDayStats);
  });

  it('returns fallback on network error', async () => {
    mockGetStats.mockRejectedValueOnce(new Error('network'));
    await expect(fetchDayStats(1)).resolves.toBe(fallbackDayStats);
  });
});

