import { describe, it, expect, vi, afterEach } from 'vitest';
import { ResponseError, Configuration } from '@offonika/diabetes-ts-sdk/runtime';
import type { ProfileSchema as Profile } from '@offonika/diabetes-ts-sdk/models';

const mockProfilesGetProfilesGet = vi.hoisted(() => vi.fn());
const mockProfilesPostProfilesPost = vi.hoisted(() => vi.fn());

vi.mock('@offonika/diabetes-ts-sdk', () => ({
  ProfilesApi: vi.fn(() => ({
    profilesGetProfilesGet: mockProfilesGetProfilesGet,
    profilesPostProfilesPost: mockProfilesPostProfilesPost,
  })),
  Configuration,
}));

import { getProfile, saveProfile } from './profile';

afterEach(() => {
  mockProfilesGetProfilesGet.mockReset();
  mockProfilesPostProfilesPost.mockReset();
});

describe('getProfile', () => {
  it('returns null on 404 response', async () => {
    const err = new ResponseError(new Response(null, { status: 404 }));
    mockProfilesGetProfilesGet.mockRejectedValueOnce(err);
    await expect(getProfile(1)).resolves.toBeNull();
  });

  it('rethrows other errors', async () => {
    const err = new ResponseError(new Response(null, { status: 500 }));
    mockProfilesGetProfilesGet.mockRejectedValueOnce(err);
    await expect(getProfile(1)).rejects.toBe(err);
  });
});

describe('saveProfile', () => {
  it('posts profile successfully', async () => {
    const profile = {} as unknown as Profile;
    const ok = { status: 'ok' };
    mockProfilesPostProfilesPost.mockResolvedValueOnce(ok);
    await expect(saveProfile(profile)).resolves.toBe(ok);
    expect(mockProfilesPostProfilesPost).toHaveBeenCalledWith({
      profileSchema: profile,
    });
  });

  it('rethrows errors from API', async () => {
    const error = new Error('fail');
    mockProfilesPostProfilesPost.mockRejectedValueOnce(error);
    await expect(saveProfile({} as unknown as Profile)).rejects.toBe(
      error,
    );
  });

  it('throws generic error for non-Error values', async () => {
    mockProfilesPostProfilesPost.mockRejectedValueOnce('bad');
    await expect(saveProfile({} as unknown as Profile)).rejects.toThrow(
      'Не удалось сохранить профиль',
    );
  });

  it('throws on error status', async () => {
    mockProfilesPostProfilesPost.mockResolvedValueOnce({ status: 'error' });
    await expect(saveProfile({} as unknown as Profile)).rejects.toThrow(
      'Не удалось сохранить профиль',
    );
  });
});

