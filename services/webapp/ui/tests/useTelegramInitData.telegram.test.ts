import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';
import * as telegramAuth from '../src/lib/telegram-auth';

describe('useTelegramInitData Telegram context', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('reads initData from Telegram WebApp and stores it', () => {
    const spy = vi.spyOn(telegramAuth, 'setTelegramInitData');
    (window as any).Telegram = { WebApp: { initData: 'from-ctx' } };

    const { result } = renderHook(() => useTelegramInitData());

    expect(result.current).toBe('from-ctx');
    expect(spy).toHaveBeenCalledWith('from-ctx');
  });
});
