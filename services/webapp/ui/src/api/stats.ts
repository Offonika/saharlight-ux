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
  const res = await fetch(`/api/analytics?telegramId=${telegramId}`);
  if (!res.ok) {
    throw new Error('Failed to fetch analytics');
  }
  const data = await res.json();
  if (!Array.isArray(data)) {
    throw new Error('Invalid analytics data');
  }
  return data as AnalyticsPoint[];
}

export async function fetchDayStats(telegramId: number): Promise<DayStats> {
  const res = await fetch(`/api/stats?telegramId=${telegramId}`);
  if (!res.ok) {
    throw new Error('Failed to fetch stats');
  }
  const data = await res.json();
  return {
    sugar: Number(data.sugar),
    breadUnits: Number(data.breadUnits),
    insulin: Number(data.insulin),
  };
}
