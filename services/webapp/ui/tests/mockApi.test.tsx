import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';

const remindersGetRaw = vi.fn();
const remindersPost = vi.fn();
const mockGetReminders = vi.fn();
const mockCreateReminder = vi.fn();
const toast = vi.fn();
const toastError = vi.fn();

vi.mock('../src/features/reminders/api/reminders', () => ({
  useRemindersApi: () => ({ remindersGetRaw, remindersPost })
}));
vi.mock('../src/hooks/use-toast', () => ({
  useToast: () => ({ toast })
}));
vi.mock('../src/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: { id: 1 }, sendData: vi.fn() })
}));
vi.mock('../src/hooks/useTelegramInitData', () => ({
  useTelegramInitData: () => null,
}));
vi.mock('../src/shared/toast', () => ({
  useToast: () => ({ success: vi.fn(), error: toastError })
}));
vi.mock('../src/api/mock-server', () => ({
  mockApi: { getReminders: mockGetReminders, createReminder: mockCreateReminder }
}));
vi.mock('../src/features/reminders/api/buildPayload', () => ({
  buildReminderPayload: (x: any) => x
}));
vi.mock('../src/features/reminders/logic/validate', () => ({
  validate: () => ({}),
  hasErrors: () => false
}));
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn()
}));

describe('mockApi not used in production', () => {
  afterEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    remindersGetRaw.mockReset();
    remindersPost.mockReset();
    mockGetReminders.mockReset();
    mockCreateReminder.mockReset();
    toast.mockReset();
    toastError.mockReset();
  });

  it('RemindersList uses toast and not mockApi in production', async () => {
    remindersGetRaw.mockRejectedValue(new Error('fail'));
    vi.stubEnv('DEV', 'false');
    const { default: RemindersList } = await import('../src/features/reminders/pages/RemindersList');
    render(<RemindersList />);
    await waitFor(() => {
      expect(remindersGetRaw).toHaveBeenCalled();
    });
    expect(mockGetReminders).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalled();
  });

  it('RemindersCreate uses toast and not mockApi in production', async () => {
    remindersPost.mockRejectedValue(new Error('fail'));
    vi.stubEnv('NODE_ENV', 'production');
    const { default: RemindersCreate } = await import('../src/features/reminders/pages/RemindersCreate');
    const { container } = render(<RemindersCreate />);
    const form = container.querySelector('form')!;
    fireEvent.submit(form);
    await waitFor(() => {
      expect(remindersPost).toHaveBeenCalled();
    });
    expect(mockCreateReminder).not.toHaveBeenCalled();
    expect(toastError).toHaveBeenCalled();
  });
});

