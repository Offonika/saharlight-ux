import type { ProfileSchema } from '@sdk';
import { api } from '@/api';

export async function getProfile(telegramId: number) {
  try {
    return await api.get<ProfileSchema>(`/profiles?telegramId=${telegramId}`);
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
  try {
    return await api.post<ProfileSchema>('/profiles', {
      telegramId,
      icr,
      cf,
      target,
      low,
      high,
    });
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось сохранить профиль: ${error.message}`);
    }
    throw error;
  }
}

export type PatchProfileDto = {
  timezone?: string | null;
  auto_detect_timezone?: boolean | null;
};

export async function patchProfile(payload: PatchProfileDto) {
  try {
    return await api.patch<unknown>('/profile', payload);
  } catch (error) {
    console.error('Failed to update profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось обновить профиль: ${error.message}`);
    }
    throw error;
  }
}
