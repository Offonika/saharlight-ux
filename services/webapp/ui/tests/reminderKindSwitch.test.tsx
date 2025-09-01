import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';

vi.mock('../src/features/reminders/api/reminders', () => ({
  useRemindersApi: () => ({ remindersPost: vi.fn() })
}));
vi.mock('../src/hooks/useTelegramInitData', () => ({
  useTelegramInitData: () => null,
}));
vi.mock('../src/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: { id: 1 }, sendData: vi.fn() })
}));
vi.mock('../src/shared/toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() })
}));
vi.mock('../src/api/mock-server', () => ({
  mockApi: { createReminder: vi.fn() }
}));
vi.mock('../src/features/reminders/api/buildPayload', () => ({
  buildReminderPayload: (x: any) => x
}));
vi.mock('../src/features/reminders/logic/validate', () => ({
  validate: () => ({}),
  hasErrors: () => false
}));
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

describe('RemindersCreate kind switch', () => {
  afterEach(() => {
    vi.resetModules();
  });

  it('clears minutesAfter when switching to at_time', async () => {
    const { default: RemindersCreate } = await import('../src/features/reminders/pages/RemindersCreate');
    const { getByRole, queryByRole } = render(<RemindersCreate />);

    fireEvent.click(getByRole('button', { name: 'После события' }));
    fireEvent.click(getByRole('button', { name: /90/ }));

    const input = getByRole('spinbutton') as HTMLInputElement;
    expect(input.value).not.toBe('');

    fireEvent.click(getByRole('button', { name: 'Время' }));

    expect(queryByRole('spinbutton')).toBeNull();
  });
});
