import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/telegram-auth', () => ({
  getTelegramAuthHeaders: () => ({ Authorization: 'tg test' }),
  setTelegramInitData: vi.fn(),
}));

const makeResponse = () =>
  new Response(JSON.stringify(['UTC']), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

describe('getTimezones', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('respects VITE_API_BASE', async () => {
    vi.stubEnv('VITE_API_BASE', 'http://example.com');
    const fetchMock = vi.fn().mockResolvedValue(makeResponse());
    vi.stubGlobal('fetch', fetchMock);
    const { getTimezones } = await import('../src/api/timezones');
    await getTimezones();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://example.com/timezones',
      expect.any(Object),
    );
  });
});
