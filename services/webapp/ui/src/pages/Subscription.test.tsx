import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, vi, beforeEach } from 'vitest';
import Subscription from './Subscription';
import { getBillingStatus } from '@/api/billing';

vi.mock('@/components/ThemeToggle', () => ({ default: () => <div /> }));
vi.mock('@/api/billing', () => ({
  getBillingStatus: vi.fn(),
  startTrial: vi.fn(),
  subscribePlan: vi.fn(),
}));

const mockedStatus = getBillingStatus as unknown as vi.Mock;

describe('Subscription states', () => {
  beforeEach(() => {
    mockedStatus.mockReset();
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
      featureFlags: { billingEnabled: true, paywallMode: 'soft' },
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
      featureFlags: { billingEnabled: true, paywallMode: 'soft' },
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
      featureFlags: { billingEnabled: true, paywallMode: 'soft' },
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
