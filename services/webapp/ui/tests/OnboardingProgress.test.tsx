import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';

vi.mock('@/shared/api/onboarding');
vi.mock('@/shared/initData', () => ({ hasInitData: vi.fn() }));

import '@testing-library/jest-dom';
import OnboardingProgress from '../src/components/OnboardingProgress';
import { getOnboardingStatus } from '../src/shared/api/onboarding';
import { hasInitData } from '../src/shared/initData';

const mockHasInitData = hasInitData as unknown as vi.Mock;

describe('OnboardingProgress', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('shows completed badge', async () => {
    mockHasInitData.mockReturnValue(true);
    (getOnboardingStatus as any).mockResolvedValue({
      completed: true,
      step: null,
      missing: [],
    });
    render(<OnboardingProgress />);
    expect(await screen.findByText('Завершено')).toBeInTheDocument();
  });

  it('shows steps when not completed', async () => {
    mockHasInitData.mockReturnValue(true);
    (getOnboardingStatus as any).mockResolvedValue({
      completed: false,
      step: 'profile',
      missing: ['profile', 'reminders'],
    });
    render(<OnboardingProgress />);
    expect(await screen.findByText('Профиль')).toBeInTheDocument();
    expect(screen.getByText('Напоминания')).toBeInTheDocument();
  });

  it('skips fetch and render without init data', () => {
    mockHasInitData.mockReturnValue(false);
    render(<OnboardingProgress />);
    expect(screen.queryByLabelText('Onboarding progress')).toBeNull();
    expect(getOnboardingStatus).not.toHaveBeenCalled();
  });
});
