import React from 'react';
import { render, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const toast = vi.fn();

vi.mock('../src/hooks/use-toast', () => ({
  useToast: () => ({ toast }),
}));

vi.mock('../src/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: null }),
}));

vi.mock('../src/hooks/useTelegramInitData', () => ({
  useTelegramInitData: vi.fn(),
}));

vi.mock('@/shared/api/onboarding', () => ({
  postOnboardingEvent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));

vi.mock('../src/pages/resolveTelegramId', () => ({
  resolveTelegramId: vi.fn(),
}));

vi.mock('../src/features/profile/api', async () => {
  const actual = await vi.importActual<typeof import('../src/features/profile/api')>(
    '../src/features/profile/api',
  );
  return {
    ...actual,
    saveProfile: vi.fn(),
    patchProfile: vi.fn(),
    getProfile: vi.fn().mockResolvedValue(null),
  };
});

import Profile from '../src/pages/Profile';
import { resolveTelegramId } from '../src/pages/resolveTelegramId';

const originalSupportedValuesOf = (Intl as any).supportedValuesOf;

describe('Profile onboarding', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (resolveTelegramId as vi.Mock).mockReturnValue(123);
    (Intl as any).supportedValuesOf = vi
      .fn()
      .mockReturnValue(['Europe/Moscow', 'Europe/Berlin']);
    const realDTF = Intl.DateTimeFormat;
    const realResolved = realDTF.prototype.resolvedOptions;
    vi.spyOn(Intl, 'DateTimeFormat').mockImplementation((...args: any[]) => {
      const formatter = new realDTF(...(args as []));
      return Object.assign(formatter, {
        resolvedOptions: () => ({
          ...realResolved.call(formatter),
          timeZone: 'Europe/Berlin',
        }),
      });
    });
  });

  afterEach(() => {
    cleanup();
    (Intl as any).supportedValuesOf = originalSupportedValuesOf;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders empty form when profile is missing (404)', async () => {
    const { getByPlaceholderText } = render(<Profile />);

    await waitFor(() => {
      expect(toast).not.toHaveBeenCalled();
    });

    expect((getByPlaceholderText('6.0') as HTMLInputElement).value).toBe('');
  });
});
