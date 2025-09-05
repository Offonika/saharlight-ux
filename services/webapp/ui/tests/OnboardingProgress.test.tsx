import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';

import OnboardingProgress from '../src/components/OnboardingProgress';
import { getOnboardingStatus } from '../src/shared/api/onboarding';
import '@testing-library/jest-dom';

vi.mock('@/shared/api/onboarding');

describe('OnboardingProgress', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('shows completed badge', async () => {
    (getOnboardingStatus as any).mockResolvedValue({
      completed: true,
      step: null,
      missing: [],
    });
    render(<OnboardingProgress />);
    expect(await screen.findByText('Завершено')).toBeInTheDocument();
  });

  it('shows steps when not completed', async () => {
    (getOnboardingStatus as any).mockResolvedValue({
      completed: false,
      step: 'profile',
      missing: ['profile', 'reminders'],
    });
    render(<OnboardingProgress />);
    expect(await screen.findByText('Профиль')).toBeInTheDocument();
    expect(screen.getByText('Напоминания')).toBeInTheDocument();
  });
});
