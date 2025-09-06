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
  const initData = getInitDataRaw();

  if (!initData) {
    return;
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }

  const res = await fetch('/api/onboarding/events', {
    method: 'POST',
    headers,
    body: JSON.stringify({ event, step, meta }),
  });
  if (!res.ok) throw new Error('Failed to post onboarding event');
}

export async function getOnboardingStatus() {
  const initData = getInitDataRaw();

  if (!initData) {
    return;
  }

  const headers: Record<string, string> = {};
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }
  const res = await fetch('/api/onboarding/status', { headers });
  if (!res.ok) throw new Error('Failed to get onboarding status');
  return res.json();
}
