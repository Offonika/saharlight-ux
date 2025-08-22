import { StatsApi } from '@offonika/diabetes-ts-sdk';
import { Configuration } from '@offonika/diabetes-ts-sdk/runtime';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

export interface AnalyticsPoint {
  date: string;
  sugar: number;
}

export interface DayStats {
  sugar: number;
  breadUnits: number;
  insulin: number;
}

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

const api = new StatsApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export async function fetchAnalytics(telegramId: number): Promise<AnalyticsPoint[]> {
  try {
    const data = await api.analyticsGet({ telegramId });
    if (!Array.isArray(data)) {
      console.error('Unexpected analytics API response:', data);
      return fallbackAnalytics;
    }
    return data as AnalyticsPoint[];
  } catch (error) {
    console.error('Failed to fetch analytics:', error);
    return fallbackAnalytics;
  }
}

export async function fetchDayStats(telegramId: number): Promise<DayStats> {
  try {
    const data = await api.statsGet({ telegramId });

    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      console.error('Unexpected stats API response:', data);
      return fallbackDayStats;
    }

    const { sugar, breadUnits, insulin } = data as Record<string, unknown>;

    if (
      typeof sugar !== 'number' ||
      !Number.isFinite(sugar) ||
      typeof breadUnits !== 'number' ||
      !Number.isFinite(breadUnits) ||
      typeof insulin !== 'number' ||
      !Number.isFinite(insulin)
    ) {
      console.error('Unexpected stats API response:', data);
      return fallbackDayStats;
    }

    return { sugar, breadUnits, insulin };
  } catch (error) {
    console.error('Failed to fetch day stats:', error);
    return fallbackDayStats;
  }
}
