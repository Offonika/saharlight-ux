import { DefaultApi, Profile } from '@sdk';

const api = new DefaultApi();

export async function saveProfile(profile: Profile) {
  try {
    return await api.profilesPost({ profile });
  } catch (error) {
    console.error('Failed to save profile:', error);
    throw new Error('Не удалось сохранить профиль');
  }
}
