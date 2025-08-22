import { AnalyticsApi, StatsApi, Configuration } from '@offonika/diabetes-ts-sdk';
import type { AnalyticsPoint, DayStats } from '@offonika/diabetes-ts-sdk/models';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

const analyticsApi = new AnalyticsApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

const statsApi = new StatsApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export const fallbackAnalytics: AnalyticsPoint[] = [
  { date: '2024-01-01', sugar: 5.5 },
  { date: '2024-01-02', sugar: 6.1 },
  { date: '2024-01-03', sugar: 5.8 },
  { date: '2024-01-04', sugar: 6.0 },
  { date: '2024-01-05', sugar: 5.4 },
];

export const fallbackDayStats: DayStats = {
  sugar: 6.2,
  breadUnits: 4,
  insulin: 12,
};

export async function fetchAnalytics(telegramId: number): Promise<AnalyticsPoint[]> {
  try {
    const data = await analyticsApi.analyticsGet({ telegramId });
    if (!data || !Array.isArray(data)) {
      console.error('Unexpected analytics API response:', data);
      return fallbackAnalytics;
    }
    return data;
  } catch (error) {
    console.error('Failed to fetch analytics:', error);
    return fallbackAnalytics;
  }
}

export async function fetchDayStats(telegramId: number): Promise<DayStats> {
  try {
    const data = await statsApi.statsGet({ telegramId });
    if (
      !data ||
      typeof data.sugar !== 'number' ||
      typeof data.breadUnits !== 'number' ||
      typeof data.insulin !== 'number'
    ) {
      console.error('Unexpected stats API response:', data);
      return fallbackDayStats;
    }
    return data;
  } catch (error) {
    console.error('Failed to fetch day stats:', error);
    return fallbackDayStats;
  }
}
