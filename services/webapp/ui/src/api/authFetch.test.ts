import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { authFetch } from './authFetch';

interface TelegramWebApp {
  initData?: string;
}

interface TelegramWindow extends Window {
  Telegram?: { WebApp?: TelegramWebApp };
}

const originalFetch = global.fetch;

describe('authFetch', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue(new Response());
    vi.stubGlobal('window', {} as TelegramWindow);
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('sets credentials and attaches init data header', async () => {
    (window as TelegramWindow).Telegram = { WebApp: { initData: 'test-data' } };
    await authFetch('/api/profile');
    const [, options] = (global.fetch as Mock).mock.calls[0] as [unknown, RequestInit];
    const headers = options.headers as Headers;
    expect(options.credentials).toBe('include');
    expect(headers.get('X-Telegram-Init-Data')).toBe('test-data');
  });
});
