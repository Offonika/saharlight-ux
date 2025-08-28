import { ProfilesApi, ProfileSchema } from '@sdk';

const api = new ProfilesApi({ basePath: '/api' });

export async function saveProfile(profile: ProfileSchema) {
  try {
    return await api.profilesPost({ profileSchema: profile });
  } catch (error) {
    console.error('Failed to save profile:', error);
    if (error instanceof Error) {
      throw new Error(`Не удалось сохранить профиль: ${error.message}`);
    }
    throw error;
  }
}
