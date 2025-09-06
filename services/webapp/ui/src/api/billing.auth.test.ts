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

  it('fails with 401 when initData missing', async () => {
    vi.doMock('@/lib/telegram-auth', () => ({
      getTelegramAuthHeaders: () => ({}) ,
    }));
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: 'unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const { getBillingStatus } = await import('./billing');
      await expect(getBillingStatus('1')).rejects.toThrow('unauthorized');
    });
  });

