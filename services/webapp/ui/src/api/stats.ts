import { tgFetch } from '../lib/tgFetch';

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

export async function fetchAnalytics(telegramId: number): Promise<AnalyticsPoint[]> {
  try {
    const res = await tgFetch(`/api/analytics?telegramId=${telegramId}`);
    if (!res.ok) {
      console.error('Analytics API request failed:', res.status);
      return fallbackAnalytics;
    }
    const data = await res.json();
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
    const res = await tgFetch(`/api/stats?telegramId=${telegramId}`);
    if (!res.ok) {
      console.error('Stats API request failed:', res.status);
      return fallbackDayStats;
    }
    const data = await res.json();

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
