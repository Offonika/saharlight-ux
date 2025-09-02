import type { ProfileSchema } from '@sdk';
import { api } from '@/api';
import type { Profile, PatchProfileDto, RapidInsulin } from './types';

export async function getProfile(telegramId: number): Promise<Profile> {
  try {
    return await api.get<Profile>(`/profiles?telegramId=${telegramId}`);
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
}: {
  telegramId: number;
  target: number;
  low: number;
  high: number;
  icr?: number;
  cf?: number;
}) {
  try {
    const body: Record<string, unknown> = {
      telegramId,
      target,
      low,
      high,
    };

    if (icr !== undefined) {
      body.icr = icr;
    }

    if (cf !== undefined) {
      body.cf = cf;
    }

    return await api.post<ProfileSchema>('/profiles', body);
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось сохранить профиль: ${error.message}`);
    }
    throw error;
  }
}

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

export type { RapidInsulin, PatchProfileDto, Profile };
