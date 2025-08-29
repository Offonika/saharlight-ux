import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';

const remindersGetRaw = vi.fn();

vi.mock('../src/features/reminders/api/reminders', () => ({
  useRemindersApi: () => ({ remindersGetRaw })
}));
vi.mock('../src/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() })
}));
vi.mock('../src/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: { id: 1 }, sendData: vi.fn() })
}));
vi.mock('../src/hooks/useTelegramInitData', () => ({
  useTelegramInitData: () => null,
}));
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

describe('RemindersList plan limit', () => {
  afterEach(() => {
    vi.resetModules();
    remindersGetRaw.mockReset();
  });

  it('updates plan limit from response headers', async () => {
    remindersGetRaw.mockResolvedValue({
      value: () => Promise.resolve([]),
      raw: { headers: { get: (key: string) => (key === 'X-Plan-Limit' ? '7' : null) } },
    });
    const onLimitChange = vi.fn();
    const { default: RemindersList } = await import('../src/features/reminders/pages/RemindersList');
    render(<RemindersList onLimitChange={onLimitChange} />);
    await waitFor(() => {
      expect(onLimitChange).toHaveBeenCalledWith(7);
    });
  });
});
