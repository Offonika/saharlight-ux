import { getTelegramAuthHeaders, setTelegramInitData } from '@/lib/telegram-auth';

export function getInitDataRaw(): string | null {
  const initData =
    (window as unknown as { Telegram?: { WebApp?: { initData?: string } } })
      .Telegram?.WebApp?.initData;

  if (initData) {
    return initData;
  }

  const urlData = new URLSearchParams(window.location.search).get(
    'tgWebAppData',
  );

  return urlData || null;
}

export async function postOnboardingEvent(
  event: string,
  step?: string,
  meta?: any,
) {
  const rawInitData = getInitDataRaw();
  if (rawInitData) {
    setTelegramInitData(rawInitData);
  }
  const headers = getTelegramAuthHeaders();
  if (!headers.Authorization) {
    return;
  }
  headers['Content-Type'] = 'application/json';

  const res = await fetch('/api/onboarding/events', {
    method: 'POST',
    headers,
    body: JSON.stringify({ event, step, meta }),
  });
  if (!res.ok) throw new Error('Failed to post onboarding event');
}

export async function getOnboardingStatus() {
  const rawInitData = getInitDataRaw();
  if (rawInitData) {
    setTelegramInitData(rawInitData);
  }
  const headers = getTelegramAuthHeaders();
  if (!headers.Authorization) {
    return;
  }
  const res = await fetch('/api/onboarding/status', { headers });
  if (!res.ok) throw new Error('Failed to get onboarding status');
  return res.json();
}
