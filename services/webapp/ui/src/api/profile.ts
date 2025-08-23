import { ProfilesApi } from '@offonika/diabetes-ts-sdk';
import {
  instanceOfProfileSchema as instanceOfProfile,
  type ProfileSchema as Profile,
} from '@offonika/diabetes-ts-sdk/models';
import { Configuration, ResponseError } from '@offonika/diabetes-ts-sdk/runtime';
import { tgFetch } from '../lib/tgFetch';
import { API_BASE } from './base';

const api = new ProfilesApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export async function getProfile(telegramId: number): Promise<Profile | null> {
  try {
    const data = await api.profilesGetProfilesGet({ telegramId });

    if (!instanceOfProfile(data)) {
      console.error('Unexpected profile API response:', data);
      throw new Error('Некорректный ответ API');
    }

    return data;
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
    const data = await api.profilesPostProfilesPost({ profileSchema: profile });
    if (data.status !== 'ok') {
      throw new Error(data.detail || 'Не удалось сохранить профиль');
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
