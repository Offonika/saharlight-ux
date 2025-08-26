import { describe, it, expect, vi, afterEach } from 'vitest';
import { ResponseError, Configuration } from '@sdk/runtime';
import type { ProfileSchema as Profile } from '@sdk/models';

const mockProfilesGet = vi.hoisted(() => vi.fn());
const mockProfilesPost = vi.hoisted(() => vi.fn());

vi.mock('@sdk', () => ({
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

  it('returns profile with quiet and sos fields', async () => {
    const profile = {
      telegramId: 1,
      icr: 0,
      cf: 0,
      target: 0,
      low: 0,
      high: 0,
      quietStart: '22:00',
      quietEnd: '06:30',
      sosContact: '+79998887766',
      sosAlertsEnabled: true,
    } as Profile;
    mockProfilesGet.mockResolvedValueOnce(profile);
    await expect(getProfile(1)).resolves.toEqual(profile);
  });
});

describe('saveProfile', () => {
  it('posts profile successfully', async () => {
    const profile = {
      telegramId: 1,
      icr: 0,
      cf: 0,
      target: 0,
      low: 0,
      high: 0,
      quietStart: '22:00',
      quietEnd: '06:30',
      sosContact: '+79998887766',
      sosAlertsEnabled: true,
    } as Profile;
    mockProfilesPost.mockResolvedValueOnce(profile);
    await expect(saveProfile(profile)).resolves.toBe(profile);
    expect(mockProfilesPost).toHaveBeenCalledWith({
      profileSchema: profile,
    });
  });

  it('rethrows errors from API', async () => {
    const error = new Error('fail');
    mockProfilesPost.mockRejectedValueOnce(error);
    await expect(saveProfile({} as unknown as Profile)).rejects.toBe(
      error,
    );
  });

  it('throws generic error for non-Error values', async () => {
    mockProfilesPost.mockRejectedValueOnce('bad');
    await expect(saveProfile({} as unknown as Profile)).rejects.toThrow(
      'Не удалось сохранить профиль',
    );
  });

  it('throws on invalid response shape', async () => {
    mockProfilesPost.mockResolvedValueOnce({} as unknown as Profile);
    await expect(saveProfile({} as unknown as Profile)).rejects.toThrow(
      'Некорректный ответ API',
    );
  });
});

