import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEffect } from 'react';

// Mocks for Profile dependencies
vi.mock('../../services/webapp/ui/src/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));
vi.mock('../../services/webapp/ui/src/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: { id: 1 } }),
}));
vi.mock('../../services/webapp/ui/src/hooks/useTelegramInitData', () => ({
  useTelegramInitData: () => ({}),
}));
vi.mock('../../services/webapp/ui/src/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));
vi.mock('../../services/webapp/ui/src/hooks/use-mobile', () => ({
  useIsMobile: () => false,
}));
vi.mock('../../services/webapp/ui/src/api/timezones', () => ({
  getTimezones: () => Promise.resolve([]),
}));
vi.mock('../../services/webapp/ui/src/features/profile/api', () => ({
  saveProfile: vi.fn(),
  getProfile: () => Promise.resolve(null),
  patchProfile: vi.fn(),
}));
vi.mock('../../services/webapp/ui/src/components/MedicalHeader', () => ({
  MedicalHeader: ({ children }: any) => <div>{children}</div>,
}));
vi.mock('../../services/webapp/ui/src/components/MedicalButton', () => ({
  default: ({ children, ...rest }: any) => <button {...rest}>{children}</button>,
}));
vi.mock('../../services/webapp/ui/src/components/ui/button', () => ({
  Button: ({ children, ...rest }: any) => <button {...rest}>{children}</button>,
}));
vi.mock('../../services/webapp/ui/src/components/ui/checkbox', () => ({
  Checkbox: (props: any) => <input type="checkbox" {...props} />, 
}));
vi.mock('../../services/webapp/ui/src/components/Modal', () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));
vi.mock('../../services/webapp/ui/src/components/HelpHint', () => ({
  default: () => <div />,
}));
vi.mock('../../services/webapp/ui/src/components/ProfileHelpSheet', () => ({
  default: () => <div />,
}));
vi.mock('../../services/webapp/ui/src/pages/resolveTelegramId', () => ({
  resolveTelegramId: () => 1,
}));

const postEventProfile = vi.fn();
vi.mock('../../services/webapp/ui/src/shared/api/onboarding', () => ({
  postOnboardingEvent: postEventProfile,
}));

import Profile from '../../services/webapp/ui/src/pages/Profile';

// Reminders dependencies
const postEventReminders = vi.fn();
vi.mock('../../services/webapp/ui/src/api/onboarding', () => ({
  postOnboardingEvent: postEventReminders,
}));
vi.mock('../../services/webapp/ui/src/features/reminders/pages/RemindersList', () => ({
  default: ({ onCountChange, onLimitChange }: any) => {
    useEffect(() => {
      onLimitChange(5);
    }, [onLimitChange]);
    return (
      <div>
        <button onClick={() => onCountChange(1)}>add</button>
      </div>
    );
  },
}));
import Reminders from '../../services/webapp/ui/src/pages/Reminders';

describe('onboarding events', () => {
  beforeEach(() => {
    postEventProfile.mockClear();
    postEventReminders.mockClear();
  });
  it('Profile sends onboarding_started when flow=onboarding', async () => {
    render(
      <MemoryRouter initialEntries={['/profile?flow=onboarding&step=profile']}>
        <QueryClientProvider client={new QueryClient()}>
          <Profile />
        </QueryClientProvider>
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(postEventProfile).toHaveBeenCalledWith('onboarding_started', 'profile');
    });
  });

  it('Reminders sends first_reminder_created on first reminder', async () => {
    render(
      <MemoryRouter initialEntries={['/reminders']}>
        <Reminders />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('add'));
    await waitFor(() => {
      expect(postEventReminders).toHaveBeenCalledWith('first_reminder_created', 'reminders');
    });
  });

  it('Reminders sends onboarding_completed when skipped', async () => {
    render(
      <MemoryRouter initialEntries={['/reminders']}>
        <Reminders />
      </MemoryRouter>
    );
    const skipBtn = screen.getByText('Пропустить пока');
    fireEvent.click(skipBtn);
    await waitFor(() => {
      expect(postEventReminders).toHaveBeenCalledWith('onboarding_completed', 'reminders', {
        skippedReminders: true,
      });
    });
  });
});
