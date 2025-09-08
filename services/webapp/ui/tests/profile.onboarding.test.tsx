import React from 'react';
import { render, cleanup, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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

let searchParams = new URLSearchParams();

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [searchParams, vi.fn()],
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
    getProfile: vi
      .fn()
      .mockRejectedValue(
        new actual.ProfileNotRegisteredError('missing'),
      ),
  };
});

import Profile from '../src/pages/Profile';
import { resolveTelegramId } from '../src/pages/resolveTelegramId';
import { postOnboardingEvent } from '../src/shared/api/onboarding';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';
import { getProfile } from '../src/features/profile/api';

const originalSupportedValuesOf = (Intl as any).supportedValuesOf;

describe('Profile onboarding', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchParams = new URLSearchParams();
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

  it('posts onboarding_started when telegram data is valid', async () => {
    searchParams = new URLSearchParams('flow=onboarding&step=1');
    (useTelegramInitData as vi.Mock).mockReturnValue('init');

    render(
      <QueryClientProvider client={new QueryClient()}>
        <Profile />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(postOnboardingEvent).toHaveBeenCalledWith(
        'onboarding_started',
        '1',
      );
    });
  });

  it('does not post onboarding_started without telegram id', async () => {
    searchParams = new URLSearchParams('flow=onboarding');
    (useTelegramInitData as vi.Mock).mockReturnValue('init');
    (resolveTelegramId as vi.Mock).mockReturnValue(undefined);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <Profile />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(postOnboardingEvent).not.toHaveBeenCalled();
    });
  });

  it('shows toast when profile is missing (404)', async () => {
    const { getByPlaceholderText } = render(
      <QueryClientProvider client={new QueryClient()}>
        <Profile />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(toast).toHaveBeenCalled();
    });

    expect((getByPlaceholderText('6.0') as HTMLInputElement).value).toBe('');
  });

  it('shows error toast on profile load failure', async () => {
    (getProfile as vi.Mock).mockRejectedValueOnce(new Error('network'));
    const { getByPlaceholderText } = render(
      <QueryClientProvider client={new QueryClient()}>
        <Profile />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(toast).toHaveBeenCalled();
    });

    expect((getByPlaceholderText('6.0') as HTMLInputElement).value).toBe('');
  });
});
