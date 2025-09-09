import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, vi, beforeEach, expect, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import Subscription from './Subscription';
import { getBillingStatus, subscribePlan } from '@/api/billing';

vi.mock('@/components/ThemeToggle', () => ({ default: () => <div /> }));
vi.mock('@/api/billing', () => ({
  getBillingStatus: vi.fn(),
  startTrial: vi.fn(),
  subscribePlan: vi.fn(),
}));
vi.mock('@/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: null }),
}));
vi.mock('@/hooks/useTelegramInitData', () => ({
  useTelegramInitData: vi.fn(),
}));
vi.mock('./resolveTelegramId', () => ({
  resolveTelegramId: vi.fn(),
}));

import { resolveTelegramId } from './resolveTelegramId';
import { useTelegramInitData } from '@/hooks/useTelegramInitData';

const mockedStatus = getBillingStatus as unknown as vi.Mock;
const mockedResolveTelegramId = resolveTelegramId as unknown as vi.Mock;
const mockedInitData = useTelegramInitData as unknown as vi.Mock;
const mockedSubscribePlan = subscribePlan as unknown as vi.Mock;

describe('Subscription states', () => {
  beforeEach(() => {
    mockedStatus.mockReset();
    mockedResolveTelegramId.mockReset();
    mockedResolveTelegramId.mockReturnValue(123);
    mockedInitData.mockReturnValue(null);
  });

  afterEach(() => {
    cleanup();
  });

  const renderPage = async (status: unknown) => {
    mockedStatus.mockResolvedValue(status);
    render(
      <MemoryRouter>
        <Subscription />
      </MemoryRouter>,
    );
    await screen.findByTestId('status-card');
  };

  it('requests billing status on mount', async () => {
    await renderPage({
      featureFlags: { billingEnabled: false, paywallMode: 'soft', testMode: true },
      subscription: null,
    });
    expect(mockedStatus).toHaveBeenCalledTimes(1);
    expect(mockedStatus).toHaveBeenCalledWith('123');
  });

  it('renders no subscription', async () => {
    await renderPage({
      featureFlags: { billingEnabled: false, paywallMode: 'soft', testMode: true },
      subscription: null,
    });
    expect(screen.getByTestId('no-sub')).toBeTruthy();
    expect(screen.getByTestId('flag-test')).toBeTruthy();
    expect(screen.getByTestId('flag-paywall')).toHaveTextContent('soft');
  });

  it('renders trial subscription', async () => {
    await renderPage({
      featureFlags: { billingEnabled: true, paywallMode: 'soft', testMode: false },
      subscription: {
        plan: 'pro',
        status: 'trial',
        provider: 'dummy',
        startDate: '2024-01-01',
        endDate: '2024-01-15',
      },
    });
    expect(screen.getByTestId('current-plan')).toHaveTextContent('pro');
    expect(screen.getByTestId('current-status')).toHaveTextContent('trial');
  });

  it('renders active subscription', async () => {
    await renderPage({
      featureFlags: { billingEnabled: true, paywallMode: 'soft', testMode: false },
      subscription: {
        plan: 'pro',
        status: 'active',
        provider: 'dummy',
        startDate: '2024-01-01',
        endDate: null,
      },
    });
    expect(screen.getByTestId('current-status')).toHaveTextContent('active');
  });

  it('renders expired subscription', async () => {
    await renderPage({
      featureFlags: { billingEnabled: true, paywallMode: 'soft', testMode: false },
      subscription: {
        plan: 'pro',
        status: 'expired',
        provider: 'dummy',
        startDate: '2024-01-01',
        endDate: '2024-02-01',
      },
    });
    expect(screen.getByTestId('current-status')).toHaveTextContent('expired');
  });
});

describe('Subscription security', () => {
  beforeEach(() => {
    mockedStatus.mockReset();
    mockedResolveTelegramId.mockReset();
    mockedResolveTelegramId.mockReturnValue(123);
    mockedInitData.mockReturnValue(null);
    mockedSubscribePlan.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('opens link without giving access to opener', async () => {
    mockedStatus.mockResolvedValue({
      featureFlags: {
        billingEnabled: true,
        paywallMode: 'soft',
        testMode: false,
      },
      subscription: null,
    });
    mockedSubscribePlan.mockResolvedValue({ url: 'https://example.com' });
    const openSpy = vi.spyOn(window, 'open').mockImplementation(
      (_url, _target, features) => ({
        opener: features?.includes('noopener') ? null : window,
      }) as any,
    );
    render(
      <MemoryRouter>
        <Subscription />
      </MemoryRouter>,
    );
    await screen.findByTestId('status-card');
    fireEvent.click(screen.getAllByRole('button', { name: 'Оформить' })[0]);
    await waitFor(() =>
      expect(openSpy).toHaveBeenCalledWith(
        'https://example.com',
        '_blank',
        'noopener,noreferrer',
      ),
    );
    const opened = openSpy.mock.results[0]?.value as any;
    expect(opened.opener).toBeNull();
    openSpy.mockRestore();
  });
});
