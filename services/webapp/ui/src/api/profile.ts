import { DefaultApi, Profile } from '@sdk';
import { Configuration, ResponseError } from '@sdk/runtime';
import { tgFetch } from '../lib/tgFetch';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';
if (!API_BASE) {
  throw new Error('VITE_API_BASE is not set and no default is provided');
}

const api = new DefaultApi(
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
