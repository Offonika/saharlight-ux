import { describe, it, expect, beforeEach } from 'vitest';
import {
  isInitDataFresh,
  getTelegramAuthHeaders,
  setTelegramInitData,
  TELEGRAM_INIT_DATA_KEY,
} from './telegram-auth';

describe('isInitDataFresh', () => {
  it('returns true for fresh auth_date', () => {
    const now = Math.floor(Date.now() / 1000);
    const initData = `auth_date=${now}`;
    expect(isInitDataFresh(initData)).toBe(true);
  });

  it('returns false for stale auth_date', () => {
    const old = Math.floor(Date.now() / 1000) - 60 * 60 * 24 - 1;
    const initData = `auth_date=${old}`;
    expect(isInitDataFresh(initData)).toBe(false);
  });

  it('returns false for future auth_date', () => {
    const future = Math.floor(Date.now() / 1000) + 61;
    const initData = `auth_date=${future}`;
    expect(isInitDataFresh(initData)).toBe(false);
  });
});

describe('getTelegramAuthHeaders', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns header for fresh init data', () => {
    const now = Math.floor(Date.now() / 1000);
    const initData = `auth_date=${now}`;
    setTelegramInitData(initData);
    expect(getTelegramAuthHeaders()).toEqual({ Authorization: `tg ${initData}` });
  });

  it('removes stale init data from storage', () => {
    const old = Math.floor(Date.now() / 1000) - 60 * 60 * 24 - 1;
    const initData = `auth_date=${old}`;
    setTelegramInitData(initData);
    expect(getTelegramAuthHeaders()).toEqual({});
    expect(localStorage.getItem(TELEGRAM_INIT_DATA_KEY)).toBeNull();
  });

  it('removes future init data from storage', () => {
    const future = Math.floor(Date.now() / 1000) + 61;
    const initData = `auth_date=${future}`;
    setTelegramInitData(initData);
    expect(getTelegramAuthHeaders()).toEqual({});
    expect(localStorage.getItem(TELEGRAM_INIT_DATA_KEY)).toBeNull();
  });
});
