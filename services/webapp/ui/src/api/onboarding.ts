import { api } from './index';

const STEP_MAP: Record<string, number> = {
  profile: 0,
  timezone: 1,
  reminders: 2,
};

export const postOnboardingEvent = (
  event: string,
  step: keyof typeof STEP_MAP,
  meta?: Record<string, unknown>,
) => api.post<{ ok: boolean }>(`/onboarding/events`, { event, step: STEP_MAP[step], meta });
