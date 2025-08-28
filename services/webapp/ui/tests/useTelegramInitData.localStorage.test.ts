import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';

describe('useTelegramInitData localStorage absence', () => {
  const original = globalThis.localStorage;

  afterEach(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: original,
      writable: true,
      configurable: true,
    });
  });

  it('returns null when localStorage.getItem throws', () => {
    Object.defineProperty(globalThis, 'localStorage', {
      value: { getItem: () => { throw new Error('boom'); } },
      configurable: true,
    });

    const { result } = renderHook(() => useTelegramInitData());

    expect(result.current).toBeNull();
  });
});
