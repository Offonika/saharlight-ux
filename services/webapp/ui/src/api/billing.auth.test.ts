import { afterEach, describe, expect, it, vi } from 'vitest';

describe('billing auth', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it('sends Authorization header when initData present', async () => {
    vi.doMock('@/lib/telegram-auth', () => ({
      getTelegramAuthHeaders: () => ({ Authorization: 'tg test' }),
      setTelegramInitData: vi.fn(),
    }));
    const fetchMock = vi.fn().mockImplementation((_: string, init: RequestInit) => {
      const headers = init.headers as Headers;
      expect(headers.get('Authorization')).toBe('tg test');
      return Promise.resolve(
        new Response(
          JSON.stringify({
            featureFlags: {
              billingEnabled: true,
              paywallMode: 'soft',
              testMode: false,
            },
            subscription: null,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      );
    });
    vi.stubGlobal('fetch', fetchMock);
    const { getBillingStatus } = await import('./billing');
    const res = await getBillingStatus('1');
    expect(res?.subscription).toBeNull();
  });

  it('redirects to Telegram when initData missing', async () => {
    vi.doMock('@/lib/telegram-auth', () => ({
      getTelegramAuthHeaders: () => ({}),
      setTelegramInitData: vi.fn(),
    }));
    const openMock = vi.fn();
    vi.stubGlobal('window', {
      location: { href: 'https://app.example', hash: '' },
      Telegram: { WebApp: { openTelegramLink: openMock } },
    });
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const { getBillingStatus } = await import('./billing');
    await expect(getBillingStatus('1')).rejects.toThrow(
      'Telegram authorization required',
    );
    expect(openMock).toHaveBeenCalledWith('https://app.example');
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

