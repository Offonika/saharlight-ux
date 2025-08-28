import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTelegram } from '../src/hooks/useTelegram';

describe('useTelegram initData fallback', () => {
  const saved = 'query=1&user=%7B%22id%22%3A1%7D';

  beforeEach(() => {
    (window as any).Telegram = {
      WebApp: {
        initDataUnsafe: {},
        ready: vi.fn(),
        expand: vi.fn(),
        onEvent: vi.fn(),
        offEvent: vi.fn(),
      },
    };
    localStorage.setItem('tg_init_data', saved);
  });

  afterEach(() => {
    delete (window as any).Telegram;
    localStorage.clear();
  });

  it('returns initData from localStorage when tg.initData missing', async () => {
    const { result } = renderHook(() => useTelegram(false));
    await waitFor(() => {
      expect(result.current.isReady).toBe(true);
    });
    expect(result.current.initData).toBe(saved);
  });

  it('returns null when initData is absent in tg and localStorage', async () => {
    localStorage.removeItem('tg_init_data');
    const { result } = renderHook(() => useTelegram(false));
    await waitFor(() => {
      expect(result.current.isReady).toBe(true);
    });
    expect(result.current.initData).toBeNull();
  });
});
