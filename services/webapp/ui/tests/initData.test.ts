import { afterEach, describe, expect, it, vi } from 'vitest';
import { hasInitData } from '../src/shared/initData';
import * as telegramAuth from '../src/lib/telegram-auth';

describe('hasInitData', () => {
  afterEach(() => {
    delete (window as any).Telegram;
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('returns true and stores when Telegram initData present', () => {
    const spy = vi.spyOn(telegramAuth, 'setTelegramInitData');
    (window as any).Telegram = { WebApp: { initData: 'init' } };
    expect(hasInitData()).toBe(true);
    expect(spy).toHaveBeenCalledWith('init');
  });

  it('returns true and stores when tgWebAppData param present', () => {
    const spy = vi.spyOn(telegramAuth, 'setTelegramInitData');
    vi.stubGlobal('location', { hash: '#tgWebAppData=from-url' } as any);
    expect(hasInitData()).toBe(true);
    expect(spy).toHaveBeenCalledWith('from-url');
  });

  it('returns false when no init data', () => {
    expect(hasInitData()).toBe(false);
  });
});
