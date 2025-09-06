import { afterEach, describe, expect, it, vi } from 'vitest';
import { hasInitData } from '../src/shared/initData';

describe('hasInitData', () => {
  afterEach(() => {
    delete (window as any).Telegram;
    vi.unstubAllGlobals();
  });

  it('returns true when Telegram initData present', () => {
    (window as any).Telegram = { WebApp: { initData: 'init' } };
    expect(hasInitData()).toBe(true);
  });

  it('returns true when tgWebAppData param present', () => {
    vi.stubGlobal('location', { search: '?tgWebAppData=from-url' } as any);
    expect(hasInitData()).toBe(true);
  });

  it('returns false when no init data', () => {
    expect(hasInitData()).toBe(false);
  });
});
