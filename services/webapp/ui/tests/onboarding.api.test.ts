import { afterEach, describe, expect, it, vi } from 'vitest';
import { postOnboardingEvent, getOnboardingStatus } from '../src/shared/api/onboarding';

describe('onboarding api', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    delete (window as any).telegramInitData;
  });

  it('throws error when postOnboardingEvent request fails', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 500 }));
    (window as any).telegramInitData = 'init';
    vi.stubGlobal('fetch', mockFetch);

    await expect(postOnboardingEvent('onboarding_started')).rejects.toThrow(
      'Failed to post onboarding event',
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/onboarding/events',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('throws error when getOnboardingStatus request fails', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 500 }));
    (window as any).telegramInitData = 'init';
    vi.stubGlobal('fetch', mockFetch);

    await expect(getOnboardingStatus()).rejects.toThrow(
      'Failed to get onboarding status',
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/onboarding/status',
      expect.any(Object),
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
    (window as any).telegramInitData = 'init';
    vi.stubGlobal('fetch', mockFetch);

    const data = await getOnboardingStatus();
    expect(data).toEqual({ step: 'profile' });
  });
});
