import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  postOnboardingEvent,
  getOnboardingStatus,
} from '../src/shared/api/onboarding';

describe('onboarding api', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    delete (window as any).Telegram;
    localStorage.clear();
  });

  it('throws error when postOnboardingEvent request fails', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 500 }));
    (window as any).Telegram = { WebApp: { initData: 'init' } };
    vi.stubGlobal('fetch', mockFetch);

    await expect(postOnboardingEvent('onboarding_started')).rejects.toThrow(
      'Failed to post onboarding event',
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/onboarding/events',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'tg init' }),
      }),
    );
  });

  it('throws error when getOnboardingStatus request fails', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 500 }));
    (window as any).Telegram = { WebApp: { initData: 'init' } };
    vi.stubGlobal('fetch', mockFetch);

    await expect(getOnboardingStatus()).rejects.toThrow(
      'Failed to get onboarding status',
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/onboarding/status',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'tg init' }),
      }),
    );
  });

  it('returns data when getOnboardingStatus succeeds', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ step: 'profile' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    (window as any).Telegram = { WebApp: { initData: 'init' } };
    vi.stubGlobal('fetch', mockFetch);

    const data = await getOnboardingStatus();
    expect(data).toEqual({ step: 'profile' });
  });

  it('skips requests when init data is missing', async () => {
    const mockFetch = vi.fn();
    vi.stubGlobal('fetch', mockFetch);

    await postOnboardingEvent('onboarding_started');
    await getOnboardingStatus();

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('uses tgWebAppData param when Telegram data missing', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal('fetch', mockFetch);
    vi.stubGlobal('location', { search: '?tgWebAppData=from-url' } as any);

    await postOnboardingEvent('onboarding_started');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/onboarding/events',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'tg from-url' }),
      }),
    );
  });
});
