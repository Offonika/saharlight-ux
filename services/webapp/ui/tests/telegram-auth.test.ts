import { afterEach, describe, expect, it } from 'vitest';
import {
  getTelegramAuthHeaders,
  setTelegramInitData,
  TELEGRAM_INIT_DATA_KEY,
} from '../src/lib/telegram-auth';

const makeInitData = (authDate: number): string =>
  new URLSearchParams({ auth_date: String(authDate) }).toString();

describe('getTelegramAuthHeaders auth_date handling', () => {
  afterEach(() => {
    setTelegramInitData('');
    localStorage.clear();
  });

  it('removes stale auth_date and returns empty headers', () => {
    const old = makeInitData(Math.floor(Date.now() / 1000) - 60 * 60 * 25);
    localStorage.setItem(TELEGRAM_INIT_DATA_KEY, old);

    const headers = getTelegramAuthHeaders();

    expect(headers).toEqual({});
    expect(localStorage.getItem(TELEGRAM_INIT_DATA_KEY)).toBeNull();
  });

  it('returns Authorization header when auth_date is fresh', () => {
    const fresh = makeInitData(Math.floor(Date.now() / 1000));
    localStorage.setItem(TELEGRAM_INIT_DATA_KEY, fresh);

    const headers = getTelegramAuthHeaders();

    expect(headers).toHaveProperty('Authorization', `tg ${fresh}`);
  });
});
