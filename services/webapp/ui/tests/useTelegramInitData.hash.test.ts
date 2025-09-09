import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';
import * as telegramAuth from '../src/lib/telegram-auth';

describe('useTelegramInitData tgWebAppData parsing', () => {
  afterEach((): void => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('reads tgWebAppData from location hash and stores it', () => {
    const spy = vi.spyOn(telegramAuth, 'setTelegramInitData');
    vi.stubGlobal('location', { hash: '#tgWebAppData=from-hash' } as any);

    const { result } = renderHook(() => useTelegramInitData());

    expect(result.current).toBe('from-hash');
    expect(spy).toHaveBeenCalledWith('from-hash');
  });

  it('falls back to localStorage when URL parsing fails', () => {
    const saved = 'from-ls';
    localStorage.setItem('tg_init_data', saved);

    class ThrowingURLSearchParams {
      constructor(_: string) {
        throw new Error('boom');
      }
      get(): string | null {
        return null;
      }
    }
    const original = URLSearchParams;
    Object.defineProperty(globalThis, 'URLSearchParams', {
      value: ThrowingURLSearchParams,
      configurable: true,
    });
    vi.stubGlobal('location', { hash: '#tgWebAppData=broken' } as any);

    const { result } = renderHook(() => useTelegramInitData());

    expect(result.current).toBe(saved);

    Object.defineProperty(globalThis, 'URLSearchParams', {
      value: original,
      configurable: true,
    });
  });
});
