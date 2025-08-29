import type { ProfileSchema } from '@sdk';
import { getTelegramAuthHeaders } from '@/lib/telegram-auth';

export async function getProfile(telegramId: number) {
  const headers = getTelegramAuthHeaders() as HeadersInit;

  try {
    const params = new URLSearchParams({ telegramId: String(telegramId) });
    const res = await fetch(`/api/profiles?${params.toString()}`, {
      method: 'GET',
      headers,
    });

    const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    if (!res.ok) {
      const msg = typeof data.detail === 'string' ? data.detail : 'Request failed';
      throw new Error(msg);
    }
    return data as ProfileSchema;
  } catch (error) {
    console.error('Failed to load profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось получить профиль: ${error.message}`);
    }
    throw error;
  }
}

export async function saveProfile({
  telegramId,
  icr,
  cf,
  target,
  low,
  high,
}: Pick<ProfileSchema, 'telegramId' | 'icr' | 'cf' | 'target' | 'low' | 'high'>) {
  const headers = {
    'Content-Type': 'application/json',
    ...getTelegramAuthHeaders(),
  } as HeadersInit;

  try {
    const res = await fetch('/api/profiles', {
      method: 'POST',
      headers,
      body: JSON.stringify({ telegramId, icr, cf, target, low, high }),
    });

    const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    if (!res.ok) {
      const msg = typeof data.detail === 'string' ? data.detail : 'Request failed';
      throw new Error(msg);
    }
    return data as ProfileSchema;
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось сохранить профиль: ${error.message}`);
    }
    throw error;
  }
}
