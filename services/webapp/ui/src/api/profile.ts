import { ProfilesApi } from '@sdk';
import {
  instanceOfProfileSchema as instanceOfProfile,
  type ProfileSchema as Profile,
} from '@sdk/models';
import { Configuration, ResponseError } from '@sdk/runtime';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

const api = new ProfilesApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

/**
 * Fetch profile by telegramId.
 * Returns null if profile is not found (404).
 */
export async function getProfile(telegramId: number): Promise<Profile | null> {
  try {
    const data = await api.profilesGet({ telegramId });

    if (!instanceOfProfile(data)) {
      console.error('Unexpected profile API response:', data);
      throw new Error('Некорректный ответ API');
    }

    return {
      ...data,
      sosContact: data.sosContact,
      sosAlertsEnabled: data.sosAlertsEnabled,
      quietStart: data.quietStart,
      quietEnd: data.quietEnd,
    };
  } catch (error) {
    console.error('Failed to fetch profile:', error);
    if (error instanceof ResponseError && error.response.status === 404) {
      return null;
    }
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось загрузить профиль');
  }
}

export async function saveProfile(profile: Profile): Promise<Profile> {
  try {
    const data = await api.profilesPost({
      profileSchema: {
        ...profile,
        sosContact: profile.sosContact,
        sosAlertsEnabled: profile.sosAlertsEnabled,
        quietStart: profile.quietStart,
        quietEnd: profile.quietEnd,
      },
    });
    if (!instanceOfProfile(data)) {
      console.error('Unexpected profile API response:', data);
      throw new Error('Некорректный ответ API');
    }
    return data;
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось сохранить профиль');
  }
}
