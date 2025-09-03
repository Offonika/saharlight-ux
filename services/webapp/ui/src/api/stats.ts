import { Configuration } from '@sdk/runtime.ts';
import { DefaultApi } from '@sdk/apis';
import type { AnalyticsPoint, DayStats } from '@sdk/models';
import { getTelegramAuthHeaders } from '@/lib/telegram-auth';

function makeApi(): DefaultApi {
  const cfg = new Configuration({
    basePath: '/api',
    headers: getTelegramAuthHeaders(),
  });
  return new DefaultApi(cfg);
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
  const api = makeApi();
  return api.getAnalyticsAnalyticsGet({ telegramId });
}

export async function fetchDayStats(
  telegramId: number,
): Promise<DayStats | null> {
  const api = makeApi();
  const data = await api.getStatsStatsGet({ telegramId });
  return data ?? null;
}
