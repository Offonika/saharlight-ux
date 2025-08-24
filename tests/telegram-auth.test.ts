import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { getTelegramAuthHeaders, TELEGRAM_INIT_DATA_KEY } from '../src/lib/telegram-auth';

describe('getTelegramAuthHeaders', () => {
  const HEADER = 'x-telegram-init-data';

  beforeEach(() => {
    // Ensure clean globals and env
    (globalThis as any).window = {};
    delete (globalThis as any).localStorage;
    (import.meta.env as any).MODE = 'production';
    delete (import.meta.env as any).VITE_TELEGRAM_INIT_DATA;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('reads init data from global Telegram WebApp', () => {
    const initData = 'globalInit';
    (globalThis as any).window = { Telegram: { WebApp: { initData } } };

    const headers = getTelegramAuthHeaders();
    expect(headers[HEADER]).toBe(initData);
  });

  it('falls back to localStorage in dev when global init data absent', () => {
    const localInit = 'localInit';
    (globalThis as any).localStorage = { getItem: vi.fn(() => localInit) };
    (import.meta.env as any).MODE = 'development';

    const headers = getTelegramAuthHeaders();
    expect(headers[HEADER]).toBe(localInit);
    expect((globalThis as any).localStorage.getItem).toHaveBeenCalledWith(TELEGRAM_INIT_DATA_KEY);
  });

  it('uses VITE_TELEGRAM_INIT_DATA env var when localStorage is empty', () => {
    (globalThis as any).localStorage = { getItem: vi.fn(() => null) };
    (import.meta.env as any).MODE = 'development';
    (import.meta.env as any).VITE_TELEGRAM_INIT_DATA = 'envInit';

    const headers = getTelegramAuthHeaders();
    expect(headers[HEADER]).toBe('envInit');
  });

  it('does not inject headers in production when no init data', () => {
    const headers = getTelegramAuthHeaders();
    expect(headers[HEADER]).toBeUndefined();
    expect(Object.keys(headers).length).toBe(0);
  });
});
