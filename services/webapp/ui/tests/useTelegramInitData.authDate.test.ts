import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';
import { TELEGRAM_INIT_DATA_KEY } from '../src/lib/telegram-auth';

const makeInitData = (authDate: number): string =>
  new URLSearchParams({ auth_date: String(authDate) }).toString();

describe('useTelegramInitData auth_date expiry', () => {
  afterEach(() => {
    localStorage.clear();
  });

  it('ignores and removes expired init data from localStorage', () => {
    const old = makeInitData(Math.floor(Date.now() / 1000) - 60 * 60 * 25);
    localStorage.setItem(TELEGRAM_INIT_DATA_KEY, old);

    const { result } = renderHook(() => useTelegramInitData());

    expect(result.current).toBeNull();
    expect(localStorage.getItem(TELEGRAM_INIT_DATA_KEY)).toBeNull();
  });
});
