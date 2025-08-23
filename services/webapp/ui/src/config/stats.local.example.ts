import type { AnalyticsPoint, DayStats } from '@/api/stats';

export default {
  analytics: [
    { date: '2024-01-01', sugar: 5.5 },
  ],
  dayStats: { sugar: 6, breadUnits: 3, insulin: 10 },
} satisfies {
  analytics?: AnalyticsPoint[];
  dayStats?: DayStats;
};
