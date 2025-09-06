import type { ProfileSchema } from '@sdk';
import { tgFetch, FetchError } from '@/lib/tgFetch';
import type { Profile, PatchProfileDto, RapidInsulin } from './types';

export async function getProfile(): Promise<Profile | null> {
  try {
    return await tgFetch<Profile>(`/profile/self`);
  } catch (error) {
    if (error instanceof FetchError) {
      if (error.status === 404) {
        return null;
      }
      console.error('Failed to load profile:', error);
      throw new Error(`Не удалось получить профиль: ${error.message}`);
    }
    console.error('Failed to load profile:', error);
    const message =
      error instanceof Error ? error.message : 'Unknown error';
    throw new Error(`Не удалось получить профиль: ${message}`);
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

    return await tgFetch<ProfileSchema>('/profiles', {
      method: 'POST',
      body,
    });
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
    // Preserve explicit `null` values to clear fields, but drop `undefined`.
    const body = Object.fromEntries(
      Object.entries(payload).filter(([, value]) => value !== undefined),
    ) as Record<string, unknown>;

    return await tgFetch<unknown>('/profile', { method: 'PATCH', body });
  } catch (error) {
    console.error('Failed to update profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось обновить профиль: ${error.message}`);
    }
    throw error;
  }
}

export type { RapidInsulin, PatchProfileDto, Profile };
