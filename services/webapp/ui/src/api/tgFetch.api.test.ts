import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { tgFetch } from '../lib/tgFetch';

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
    try {
      global.fetch = originalFetch;
      vi.restoreAllMocks();
      vi.unstubAllGlobals();
    } finally {
      vi.useRealTimers();
    }
  });

  it('sets credentials and attaches init data header', async () => {
    (window as TelegramWindow).Telegram = { WebApp: { initData: 'test-data' } };
    await tgFetch('/api/profile');
    const [, options] = (global.fetch as Mock).mock.calls[0] as [unknown, RequestInit];
    const headers = options.headers as Headers;
    expect(options.credentials).toBe('include');
    expect(headers.get('X-Telegram-Init-Data')).toBe('test-data');
  });

  it('throws a network error on fetch failure', async () => {
    (global.fetch as Mock).mockRejectedValue(new DOMException('fail', 'SecurityError'));
    await expect(tgFetch('/api/profile')).rejects.toThrow('Проблема с сетью');
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

    const promise = tgFetch('/api/profile');
    vi.advanceTimersByTime(10_000);
    await expect(promise).rejects.toThrow('Превышено время ожидания');
  });
});
