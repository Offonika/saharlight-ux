import { DefaultApi, Profile } from '@sdk';
import { Configuration, ResponseError } from '@sdk/runtime';

const api = new DefaultApi(
  new Configuration({ basePath: import.meta.env.VITE_API_BASE }),
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
      throw new Error(`Не удалось загрузить профиль: ${error.message}`);
    }
    throw error;
  }
}

export async function saveProfile(profile: Profile) {
  try {
    return await api.profilesPost({ profile });
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось сохранить профиль: ${error.message}`);
    }
    throw error;
  }
}
