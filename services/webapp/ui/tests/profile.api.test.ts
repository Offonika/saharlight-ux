import { afterEach, describe, expect, it, vi } from 'vitest';
import { getProfile, saveProfile, patchProfile } from '../src/features/profile/api';

vi.mock('@/lib/telegram-auth', () => ({
  getTelegramAuthHeaders: () => ({}),
}));

describe('profile api', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('throws error when getProfile request fails', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: 'boom' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', mockFetch);

    await expect(getProfile(1)).rejects.toThrow(
      'Не удалось получить профиль: boom',
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/profile?telegramId=1',
      expect.any(Object),
    );
  });

  it('returns null when profile not found', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: 'missing' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', mockFetch);

    const result = await getProfile(1);
    expect(result).toBeNull();
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/profile?telegramId=1',
      expect.any(Object),
    );
  });

  it('throws error when getProfile returns invalid JSON', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        new Response('not-json', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', mockFetch);

    await expect(getProfile(1)).rejects.toThrow(
      'Не удалось получить профиль: Некорректный ответ сервера',
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/profile?telegramId=1',
      expect.any(Object),
    );
  });

  it('throws error when saveProfile request fails', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: 'fail' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', mockFetch);

    await expect(
      saveProfile({ telegramId: 1, icr: 1, cf: 2, target: 5, low: 4, high: 10 }),
    ).rejects.toThrow('Не удалось сохранить профиль: fail');
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/profile',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('does not send insulin fields for non-insulin profiles', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ telegramId: 1, target: 5, low: 4, high: 10 }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      );
    vi.stubGlobal('fetch', mockFetch);

    await saveProfile({
      telegramId: 1,
      target: 5,
      low: 4,
      high: 10,
      timezone: 'UTC',
      timezoneAuto: false,
      quietStart: '23:00',
      quietEnd: '07:00',
      sosAlertsEnabled: true,
      sosContact: null,
      therapyType: 'none',
    });

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/profile',
      expect.objectContaining({ method: 'POST', body: expect.any(String) }),
    );
    const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
    expect(body).toEqual({
      telegramId: 1,
      target: 5,
      low: 4,
      high: 10,
      timezone: 'UTC',
      timezoneAuto: false,
      quietStart: '23:00',
      quietEnd: '07:00',
      sosAlertsEnabled: true,
      sosContact: null,
      therapyType: 'none',
    });
  });

  it('throws error when patchProfile request fails', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: 'fail' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', mockFetch);

    await expect(
      patchProfile({ timezone: 'Europe/Moscow', timezoneAuto: true }),
    ).rejects.toThrow('Не удалось обновить профиль: fail');
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/profile',
      expect.objectContaining({ method: 'PATCH' }),
    );
  });
});
