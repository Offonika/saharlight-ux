import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { useTelegramInitData } from '../src/hooks/useTelegramInitData';

describe('useTelegramInitData', () => {
  afterEach(() => {
    delete (window as any).Telegram;
    localStorage.clear();
  });

  it('returns Telegram initData and stores it', () => {
    const now = Math.floor(Date.now() / 1000);
    const init = `auth_date=${now}`;
    (window as any).Telegram = { WebApp: { initData: init } };

    const { result } = renderHook(() => useTelegramInitData());

    expect(result.current).toBe(init);
    expect(localStorage.getItem('tg_init_data')).toBe(init);
  });

  it('returns initData from localStorage when valid', () => {
    const now = Math.floor(Date.now() / 1000);
    const saved = `auth_date=${now}`;
    localStorage.setItem('tg_init_data', saved);

    const { result } = renderHook(() => useTelegramInitData());

    expect(result.current).toBe(saved);
  });

  it('removes outdated initData', () => {
    const past = Math.floor(Date.now() / 1000) - 25 * 60 * 60;
    const old = `auth_date=${past}`;
    localStorage.setItem('tg_init_data', old);

    const { result } = renderHook(() => useTelegramInitData());

    expect(result.current).toBeNull();
    expect(localStorage.getItem('tg_init_data')).toBeNull();
  });
});

