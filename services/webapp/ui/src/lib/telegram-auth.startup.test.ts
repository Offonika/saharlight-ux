import { afterEach, describe, expect, it, vi } from 'vitest';

// This test verifies that the module initializes Telegram auth data on load
// using the global Telegram object.
describe('telegram-auth startup', () => {
  afterEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('loads init data from Telegram global object', async () => {
    const now = Math.floor(Date.now() / 1000);
    vi.stubGlobal('Telegram', { WebApp: { initData: `auth_date=${now}` } });
    const mod = await import('./telegram-auth?startup');
    expect(mod.getTelegramAuthHeaders()).toEqual({
      Authorization: `tg auth_date=${now}`,
    });
  });
});
