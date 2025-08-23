import { DefaultApi } from '@offonika/diabetes-ts-sdk';
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

interface FallbackConfig {
  analytics?: AnalyticsPoint[];
  dayStats?: DayStats;
}

const parseEnvJSON = <T>(raw: string | undefined): T | undefined => {
  if (!raw) return undefined;
  try {
    return JSON.parse(raw) as T;
  } catch (error) {
    console.error('Invalid JSON in env fallback:', error);
    return undefined;
  }
};

const envConfig: FallbackConfig = {
  analytics: parseEnvJSON<AnalyticsPoint[]>(
    import.meta.env.VITE_FALLBACK_ANALYTICS,
  ),
  dayStats: parseEnvJSON<DayStats>(import.meta.env.VITE_FALLBACK_DAY_STATS),
};

const localConfigModules = import.meta.glob(
  '../config/stats.local.{ts,js,json}',
  { eager: true },
) as Record<string, { default: FallbackConfig }>;

const localOverrides =
  Object.values(localConfigModules)[0]?.default ?? ({} as FallbackConfig);

const overrides: FallbackConfig = {
  ...envConfig,
  ...localOverrides,
};

function generateRecentAnalytics(days = 5): AnalyticsPoint[] {
  const today = new Date();
  return Array.from({ length: days }, (_, idx) => {
    const date = new Date(today);
    date.setDate(today.getDate() - (days - idx - 1));
    return { date: date.toISOString().split('T')[0], sugar: 5.5 };
  });
}

export function getFallbackAnalytics(): AnalyticsPoint[] {
  return overrides.analytics ?? generateRecentAnalytics();
}

export function getFallbackDayStats(): DayStats {
  return (
    overrides.dayStats ?? {
      sugar: 6.2,
      breadUnits: 4,
      insulin: 12,
    }
  );
}

export const fallbackAnalytics = getFallbackAnalytics();

export const fallbackDayStats = getFallbackDayStats();

const api = new DefaultApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export async function fetchAnalytics(telegramId: number): Promise<AnalyticsPoint[]> {
  try {
    const data = await api.getAnalyticsAnalyticsGet({ telegramId });
    if (!Array.isArray(data)) {
      console.error('Unexpected analytics API response:', data);
      return getFallbackAnalytics();
    }
    return data as AnalyticsPoint[];
  } catch (error) {
    console.error('Failed to fetch analytics:', error);
    return getFallbackAnalytics();
  }
}

export async function fetchDayStats(telegramId: number): Promise<DayStats> {
  try {
    const data = await api.getStatsStatsGet({ telegramId });

    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      console.error('Unexpected stats API response:', data);
      return getFallbackDayStats();
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
      return getFallbackDayStats();
    }

    return { sugar, breadUnits, insulin };
  } catch (error) {
    console.error('Failed to fetch day stats:', error);
    return getFallbackDayStats();
  }
}
