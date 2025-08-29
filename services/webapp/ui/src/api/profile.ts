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

    if (!res.ok) {
      const errorText = await res.text().catch(() => '');
      const msg = errorText || 'Request failed';
      throw new Error(msg);
    }
    const data = (await res.json()) as Record<string, unknown>;
    return data as ProfileSchema;
  } catch (error) {
    console.error('Failed to load profile:', error);
    if (error instanceof SyntaxError) {
      throw new Error('Не удалось получить профиль: некорректный ответ сервера');
    }
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

    if (!res.ok) {
      const errorText = await res.text().catch(() => '');
      const msg = errorText || 'Request failed';
      throw new Error(msg);
    }
    const data = (await res.json()) as Record<string, unknown>;
    return data as ProfileSchema;
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось сохранить профиль: ${error.message}`);
    }
    throw error;
  }
}

export async function patchProfile({
  timezone,
  timezone_auto,
}: {
  timezone: string
  timezone_auto: boolean
}) {
  const headers = {
    'Content-Type': 'application/json',
    ...getTelegramAuthHeaders(),
  } as HeadersInit

  try {
    const res = await fetch('/api/profile', {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ timezone, timezone_auto }),
    })

    if (!res.ok) {
      const errorText = await res.text().catch(() => '')
      const msg = errorText || 'Request failed'
      throw new Error(msg)
    }

    return (await res.json().catch(() => ({}))) as unknown
  } catch (error) {
    console.error('Failed to update profile:', error)
    if (error instanceof Error) {
      throw new Error(`Не удалось обновить профиль: ${error.message}`)
    }
    throw error
  }
}
