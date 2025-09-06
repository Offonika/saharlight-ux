import { describe, expect, it, beforeEach, vi } from 'vitest';

const mockGetAnalytics = vi.fn();
const mockGetStats = vi.fn();

const configInstance = {};

vi.mock('@sdk/runtime.ts', () => ({
  Configuration: vi.fn(() => configInstance),
}));

vi.mock('@sdk/apis', () => ({
  DefaultApi: vi.fn().mockImplementation(() => ({
    getAnalyticsAnalyticsGet: mockGetAnalytics,
    getStatsStatsGet: mockGetStats,
  })),
}));

vi.mock('@/lib/telegram-auth', () => ({
  getTelegramAuthHeaders: vi.fn(() => ({ Authorization: 'tg test' })),
}));

import { fetchAnalytics, fetchDayStats } from './stats';
import { Configuration } from '@sdk/runtime.ts';
import { DefaultApi } from '@sdk/apis';

describe('stats api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetchAnalytics calls SDK method', async () => {
    const points = [{ date: '2024-01-01', sugar: 5 }];
    mockGetAnalytics.mockResolvedValue(points);

    const res = await fetchAnalytics(1);

    expect(Configuration).toHaveBeenCalledWith({
      basePath: '/api',
      headers: { Authorization: 'tg test' },
    });
    expect(DefaultApi).toHaveBeenCalledWith(configInstance);
    expect(mockGetAnalytics).toHaveBeenCalledWith({ telegramId: 1 });
    expect(res).toEqual(points);
  });

  it('fetchDayStats calls SDK method', async () => {
    const stats = { sugar: 6.2, breadUnits: 4, insulin: 12 };
    mockGetStats.mockResolvedValue(stats);

    const res = await fetchDayStats(2);

    expect(Configuration).toHaveBeenCalledWith({
      basePath: '/api',
      headers: { Authorization: 'tg test' },
    });
    expect(DefaultApi).toHaveBeenCalledWith(configInstance);
    expect(mockGetStats).toHaveBeenCalledWith({ telegramId: 2 });
    expect(res).toEqual(stats);
  });
});
