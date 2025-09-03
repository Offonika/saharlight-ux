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

export async function fetchAnalytics(telegramId: number): Promise<AnalyticsPoint[]> {
  const api = makeApi();
  return api.getAnalyticsAnalyticsGet({ telegramId });
}

export async function fetchDayStats(
  telegramId: number,
): Promise<DayStats | null | undefined> {
  const api = makeApi();
  return api.getStatsStatsGet({ telegramId });
}
