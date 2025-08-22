import { describe, it, expect, vi, afterEach } from 'vitest';

const mockAnalyticsGet = vi.hoisted(() => vi.fn());
const mockStatsGet = vi.hoisted(() => vi.fn());

vi.mock('@offonika/diabetes-ts-sdk', () => ({
  AnalyticsApi: vi.fn(() => ({ analyticsGet: mockAnalyticsGet })),
  StatsApi: vi.fn(() => ({ statsGet: mockStatsGet })),
  Configuration: class {},
}));

import {
  fetchAnalytics,
  fetchDayStats,
  fallbackAnalytics,
  fallbackDayStats,
} from './stats';

afterEach(() => {
  mockAnalyticsGet.mockReset();
  mockStatsGet.mockReset();
});

describe('fetchAnalytics', () => {
  it('returns analytics on valid response', async () => {
    const analytics = [
      { date: '2024-02-01', sugar: 5.5 },
      { date: '2024-02-02', sugar: 6.1 },
    ];
    mockAnalyticsGet.mockResolvedValueOnce(analytics as any);
    await expect(fetchAnalytics(1)).resolves.toEqual(analytics);
    expect(mockAnalyticsGet).toHaveBeenCalledWith({ telegramId: 1 });
  });

  it('returns fallback on invalid response', async () => {
    mockAnalyticsGet.mockResolvedValueOnce({ foo: 'bar' } as any);
    await expect(fetchAnalytics(1)).resolves.toBe(fallbackAnalytics);
  });

  it('returns fallback on network error', async () => {
    mockAnalyticsGet.mockRejectedValueOnce(new Error('network'));
    await expect(fetchAnalytics(1)).resolves.toBe(fallbackAnalytics);
  });
});

describe('fetchDayStats', () => {
  it('returns stats on valid response', async () => {
    const stats = { sugar: 5.7, breadUnits: 3, insulin: 10 } as any;
    mockStatsGet.mockResolvedValueOnce(stats);
    await expect(fetchDayStats(1)).resolves.toEqual(stats);
    expect(mockStatsGet).toHaveBeenCalledWith({ telegramId: 1 });
  });

  it('returns fallback on invalid response', async () => {
    mockStatsGet.mockResolvedValueOnce({ sugar: 'bad' } as any);
    await expect(fetchDayStats(1)).resolves.toBe(fallbackDayStats);
  });

  it('returns fallback on network error', async () => {
    mockStatsGet.mockRejectedValueOnce(new Error('network'));
    await expect(fetchDayStats(1)).resolves.toBe(fallbackDayStats);
  });
});

