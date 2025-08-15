import { DefaultApi, Profile } from '@sdk';
import { Configuration } from '@sdk/runtime';

const api = new DefaultApi(
  new Configuration({ basePath: import.meta.env.VITE_API_BASE }),
);

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
