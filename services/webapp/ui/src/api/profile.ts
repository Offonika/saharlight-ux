import { ProfilesApi, Profile } from '@sdk';

const api = new ProfilesApi();

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
