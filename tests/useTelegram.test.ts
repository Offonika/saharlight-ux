import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { useTelegram } from '../services/webapp/ui/src/hooks/useTelegram';

describe('useTelegram hook fallback', () => {
  beforeEach(() => {
    (window as any).Telegram = {
      WebApp: {
        initData: '',
        initDataUnsafe: {},
        ready: vi.fn(),
        expand: vi.fn(),
        onEvent: vi.fn(),
        offEvent: vi.fn(),
      },
    };
    (global as any).fetch = vi.fn().mockResolvedValue({ ok: false });
    Object.defineProperty(document, 'cookie', {
      writable: true,
      value: '',
    });
  });

  afterEach(() => {
    delete (window as any).Telegram;
    vi.restoreAllMocks();
  });

  it('returns fallback state when initData is missing', async () => {
    const { result } = renderHook(() => useTelegram(false));
    await waitFor(() => {
      expect(result.current.isReady).toBe(true);
    });
    await waitFor(() => {
      expect(result.current.error?.code).toBe('no-user');
      expect(result.current.error?.message).toBeUndefined();
    });
    expect(result.current.user).toBeNull();
  });
});

describe('useTelegram hook init error', () => {
  beforeEach(() => {
    (window as any).Telegram = {
      WebApp: {
        initData: '',
        initDataUnsafe: {},
        ready: vi.fn(() => {
          throw new Error('init failed');
        }),
        expand: vi.fn(),
      },
    };
  });

  afterEach(() => {
    delete (window as any).Telegram;
    vi.restoreAllMocks();
  });

  it('sets error when initialization fails', async () => {
    const { result } = renderHook(() => useTelegram(false));
    await waitFor(() => {
      expect(result.current.error?.code).toBe('unknown');
      expect(result.current.error?.message).toBe('init failed');
    });
    expect(result.current.isReady).toBe(true);
  });
});
