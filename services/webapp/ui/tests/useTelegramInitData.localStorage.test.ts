import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';

describe('useTelegramInitData when localStorage unavailable', () => {
  const original = globalThis.localStorage;

  afterEach(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: original,
    });
  });

  it('returns null if localStorage.getItem throws', () => {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: {
        getItem: () => {
          throw new Error('fail');
        },
      },
    });
    const { result } = renderHook(() => useTelegramInitData());
    expect(result.current).toBeNull();
  });

  it('returns null if localStorage is undefined', () => {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: undefined,
    });
    const { result } = renderHook(() => useTelegramInitData());
    expect(result.current).toBeNull();
  });
});
