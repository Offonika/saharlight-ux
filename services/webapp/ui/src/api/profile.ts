import type { ProfileSchema } from '@sdk';
import { getTelegramAuthHeaders } from '@/lib/telegram-auth';

export async function saveProfile({
  telegramId,
  icr,
  target,
  low,
  high,
}: Pick<ProfileSchema, 'telegramId' | 'icr' | 'target' | 'low' | 'high'>) {
  const headers = {
    'Content-Type': 'application/json',
    ...getTelegramAuthHeaders(),
  } as HeadersInit;

  try {
    const res = await fetch('/api/profiles', {
      method: 'POST',
      headers,
      body: JSON.stringify({ telegramId, icr, target, low, high }),
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
