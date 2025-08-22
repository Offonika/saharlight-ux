import { ProfilesApi, Configuration } from '@offonika/diabetes-ts-sdk';
import type { Profile } from '@offonika/diabetes-ts-sdk/models';
import { ResponseError } from '@offonika/diabetes-ts-sdk/runtime';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

const api = new ProfilesApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export async function getProfile(telegramId: number): Promise<Profile | null> {
  try {
    return await api.profilesGet({ telegramId });
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

export async function saveProfile(profile: Profile) {
  try {
    return await api.profilesPost({ profile });
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Не удалось сохранить профиль');
  }
}
