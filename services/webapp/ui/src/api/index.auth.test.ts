import { afterEach, describe, expect, it, vi } from 'vitest';

// Ensures that api.ts attaches Telegram auth headers to requests

describe('api client telegram auth', () => {
  afterEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('sends Authorization header from getTelegramAuthHeaders', async () => {
    vi.doMock('@/lib/telegram-auth', () => ({
      getTelegramAuthHeaders: () => ({ Authorization: 'tg test' }),
    }));
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response('{}', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const { api } = await import('./index');
    await api.get('/foo');
    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('tg test');
  });
});
