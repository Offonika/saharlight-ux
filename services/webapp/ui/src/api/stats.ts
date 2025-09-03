import { http } from './http';

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
  const data = await http.get<unknown>(`/analytics?telegramId=${telegramId}`);
  if (!Array.isArray(data)) {
    throw new Error('Invalid analytics data');
  }
  return data as AnalyticsPoint[];
}

export async function fetchDayStats(
  telegramId: number,
): Promise<DayStats | null> {
  const data = await http.get<unknown | null>(`/stats?telegramId=${telegramId}`);

  if (data === null) {
    return null;
  }

  if (typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('Invalid stats data');
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
}
