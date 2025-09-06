import type { ProfileSchema } from '@sdk';
import { tgFetch, FetchError } from '@/lib/tgFetch';
import type { Profile, PatchProfileDto, RapidInsulin } from './types';

export async function getProfile(telegramId: number): Promise<Profile | null> {
  try {
    return await tgFetch<Profile>(
      `/profiles?telegramId=${telegramId}`,
    );
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

export interface SaveProfileDto {
  telegramId: number;
  target: number;
  low: number;
  high: number;
  icr?: number;
  cf?: number;
  quietStart?: string | null;
  quietEnd?: string | null;
  timezone?: string | null;
  timezoneAuto?: boolean | null;
  dia?: number;
  preBolus?: number;
  roundStep?: number;
  carbUnits?: 'g' | 'xe';
  gramsPerXe?: number;
  rapidInsulinType?: RapidInsulin | null;
  maxBolus?: number;
  afterMealMinutes?: number;
  sosContact?: string | null;
  sosAlertsEnabled?: boolean;
  therapyType?: string;
}

export async function saveProfile(payload: SaveProfileDto) {
  try {
    const body = Object.fromEntries(
      Object.entries({
        telegramId: payload.telegramId,
        icr: payload.icr,
        cf: payload.cf,
        target: payload.target,
        low: payload.low,
        high: payload.high,
        quietStart: payload.quietStart,
        quietEnd: payload.quietEnd,
        timezone: payload.timezone,
        timezoneAuto: payload.timezoneAuto,
        dia: payload.dia,
        preBolus: payload.preBolus,
        roundStep: payload.roundStep,
        carbUnits: payload.carbUnits,
        gramsPerXe: payload.gramsPerXe,
        rapidInsulinType: payload.rapidInsulinType,
        maxBolus: payload.maxBolus,
        afterMealMinutes: payload.afterMealMinutes,
        sosContact: payload.sosContact,
        sosAlertsEnabled: payload.sosAlertsEnabled,
        therapyType: payload.therapyType,
      }).filter(([, value]) => value !== undefined),
    );

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
