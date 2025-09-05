export async function postOnboardingEvent(event: string, step?: string, meta?: any) {
  const initData = (window as any).telegramInitData || '';
  const res = await fetch('/api/onboarding/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Telegram-Init-Data': initData },
    body: JSON.stringify({ event, step, meta }),
  });
  if (!res.ok) throw new Error('Failed to post onboarding event');
}

export async function getOnboardingStatus() {
  const initData = (window as any).telegramInitData || '';
  const res = await fetch('/api/onboarding/status', { headers: { 'X-Telegram-Init-Data': initData } });
  if (!res.ok) throw new Error('Failed to get onboarding status');
  return res.json();
}
