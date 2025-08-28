import { describe, it, expect } from 'vitest';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';

describe('useTelegramInitData', () => {
  it('returns null when localStorage is inaccessible', () => {
    const original = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: undefined,
    });

    expect(useTelegramInitData()).toBeNull();

    if (original) {
      Object.defineProperty(globalThis, 'localStorage', original);
    } else {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (globalThis as any).localStorage;
    }
  });
});
