import { setTelegramInitData } from '@/lib/telegram-auth';
import { buildHeaders } from '@/api/http';

const STEP_MAP = {
  profile: 0,
  timezone: 1,
  reminders: 2,
} as const;

export type OnboardingStep = keyof typeof STEP_MAP;

export function isValidOnboardingStep(
  step: string | null,
): step is OnboardingStep {
  return Boolean(step && step in STEP_MAP);
}

export function getInitDataRaw(): string | null {
  const initData =
    (window as unknown as { Telegram?: { WebApp?: { initData?: string } } })
      .Telegram?.WebApp?.initData;

  if (initData) {
    return initData;
  }

  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash;
  const urlData = new URLSearchParams(hash).get('tgWebAppData');

  return urlData || null;
}

export async function postOnboardingEvent(
  event: string,
  step?: OnboardingStep,
  meta?: any,
) {
  const rawInitData = getInitDataRaw();
  if (rawInitData) {
    setTelegramInitData(rawInitData);
  }
  const stepNumber = step ? STEP_MAP[step] : null;
  const body = JSON.stringify({ event, step: stepNumber, meta });
  const headers = buildHeaders({ headers: {}, body }, true);
  const res = await fetch('/api/onboarding/events', {
    method: 'POST',
    headers,
    body,
  });
  if (!res.ok) throw new Error('Failed to post onboarding event');
}

export async function getOnboardingStatus() {
  const rawInitData = getInitDataRaw();
  if (rawInitData) {
    setTelegramInitData(rawInitData);
  }
  const headers = buildHeaders({ headers: {} }, true);
  const res = await fetch('/api/onboarding/status', { headers });
  if (!res.ok) throw new Error('Failed to get onboarding status');
  return res.json();
}
