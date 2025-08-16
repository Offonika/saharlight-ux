import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { tgFetch } from './tgFetch';

interface TelegramWebApp {
  initData?: string;
}

interface TelegramWindow extends Window {
  Telegram?: { WebApp?: TelegramWebApp };
}

const originalFetch = global.fetch;

describe('tgFetch', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue(new Response());
    vi.stubGlobal('window', {} as TelegramWindow);
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('attaches X-Telegram-Init-Data header when init data is present', async () => {
    (window as TelegramWindow).Telegram = { WebApp: { initData: 'test-data' } };
    await tgFetch('/api/profile/self');
    const [, options] = (global.fetch as Mock).mock.calls[0] as [unknown, RequestInit];
    const headers = options.headers as Headers;
    expect(headers.get('X-Telegram-Init-Data')).toBe('test-data');
    expect(options.credentials).toBe('include');
  });

  it('does not set header when init data is absent', async () => {
    (window as TelegramWindow).Telegram = { WebApp: {} };
    await tgFetch('/api/profile/self');
    const [, options] = (global.fetch as Mock).mock.calls[0] as [unknown, RequestInit];
    const headers = options.headers as Headers;
    expect(headers.has('X-Telegram-Init-Data')).toBe(false);
    expect(options.credentials).toBe('include');
  });

  it('allows overriding credentials', async () => {
    await tgFetch('/api/profile/self', { credentials: 'omit' });
    const [, options] = (global.fetch as Mock).mock.calls[0] as [unknown, RequestInit];
    expect(options.credentials).toBe('omit');
  });

  it('throws a network error on fetch failure', async () => {
    (global.fetch as Mock).mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(tgFetch('/api/profile/self')).rejects.toThrow('Проблема с сетью');
  });

  it('aborts request after timeout', async () => {
    vi.useFakeTimers();
    (global.fetch as Mock).mockImplementation((_, options: RequestInit) =>
      new Promise((_resolve, reject) => {
        options.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        );
      }),
    );

    const promise = tgFetch('/api/profile/self');
    vi.advanceTimersByTime(10_000);
    await expect(promise).rejects.toThrow('Превышено время ожидания');
    vi.useRealTimers();
  });
});
