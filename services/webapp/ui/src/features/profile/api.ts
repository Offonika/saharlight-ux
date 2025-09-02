import type { ProfileSchema } from '@sdk';
import { api } from '@/api';

export interface ExtendedProfileSchema extends ProfileSchema {
  dia?: number | null;
  preBolus?: number | null;
  roundStep?: number | null;
  carbUnit?: 'g' | 'xe' | null;
  gramsPerXe?: number | null;
  rapidInsulinType?: string | null;
  maxBolus?: number | null;
  defaultAfterMealMinutes?: number | null;
  therapyType?: 'insulin' | 'tablets' | 'none' | 'mixed' | null;
}

export async function getProfile(telegramId: number) {
  try {
    return await api.get<ExtendedProfileSchema>(`/profiles?telegramId=${telegramId}`);
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
  timezoneAuto?: boolean | null;
  dia?: number | null;
  preBolus?: number | null;
  roundStep?: number | null;
  carbUnit?: 'g' | 'xe' | null;
  gramsPerXe?: number | null;
  rapidInsulinType?: string | null;
  maxBolus?: number | null;
  defaultAfterMealMinutes?: number | null;
};

export async function patchProfile(payload: PatchProfileDto) {
  try {
    const body: Record<string, unknown> = {};
    Object.entries(payload).forEach(([key, value]) => {
      if (value !== undefined) {
        body[key] = value;
      }
    });
    return await api.patch<unknown>('/profile', body);
  } catch (error) {
    console.error('Failed to update profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось обновить профиль: ${error.message}`);
    }
    throw error;
  }
}
