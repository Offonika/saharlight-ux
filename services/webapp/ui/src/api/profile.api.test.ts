import { describe, it, expect, vi, afterEach } from 'vitest';
import { ResponseError, Configuration } from '@offonika/diabetes-ts-sdk/runtime';
import type { Profile } from '@offonika/diabetes-ts-sdk/models';

const mockProfilesGet = vi.hoisted(() => vi.fn());
const mockProfilesPost = vi.hoisted(() => vi.fn());

vi.mock('@offonika/diabetes-ts-sdk', () => ({
  ProfilesApi: vi.fn(() => ({
    profilesGet: mockProfilesGet,
    profilesPost: mockProfilesPost,
  })),
  Configuration,
}));

import { getProfile, saveProfile } from './profile';

afterEach(() => {
  mockProfilesGet.mockReset();
  mockProfilesPost.mockReset();
});

describe('getProfile', () => {
  it('returns null on 404 response', async () => {
    const err = new ResponseError(new Response(null, { status: 404 }));
    mockProfilesGet.mockRejectedValueOnce(err);
    await expect(getProfile(1)).resolves.toBeNull();
  });

  it('rethrows other errors', async () => {
    const err = new ResponseError(new Response(null, { status: 500 }));
    mockProfilesGet.mockRejectedValueOnce(err);
    await expect(getProfile(1)).rejects.toBe(err);
  });
});

describe('saveProfile', () => {
  it('posts profile successfully', async () => {
    const profile = {} as unknown as Profile;
    const response = { ok: true };
    mockProfilesPost.mockResolvedValueOnce(response);
    await expect(saveProfile(profile)).resolves.toBe(response);
    expect(mockProfilesPost).toHaveBeenCalledWith({ profile });
  });

  it('rethrows errors from API', async () => {
    const error = new Error('fail');
    mockProfilesPost.mockRejectedValueOnce(error);
    await expect(saveProfile({} as unknown as Profile)).rejects.toBe(error);
  });

  it('throws generic error for non-Error values', async () => {
    mockProfilesPost.mockRejectedValueOnce('bad');
    await expect(saveProfile({} as unknown as Profile)).rejects.toThrow('Не удалось сохранить профиль');
  });
});

