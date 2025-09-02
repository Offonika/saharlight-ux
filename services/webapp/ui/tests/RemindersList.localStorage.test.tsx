import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

import RemindersList from '../src/features/reminders/pages/RemindersList';

vi.mock('../src/features/reminders/api/reminders', () => ({
  useRemindersApi: () => ({
    remindersGetRaw: vi.fn().mockResolvedValue({
      value: async () => [
        {
          id: 1,
          telegramId: 1,
          type: 'sugar',
          kind: 'at_time',
          isEnabled: true,
        },
      ],
      raw: { headers: new Headers() },
    }),
  }),
}));

vi.mock('@/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: { id: 1 } }),
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

describe('RemindersList localStorage fallback', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: () => {
          throw new Error('blocked');
        },
        setItem: vi.fn(),
      },
    });
  });

  afterEach(() => {
    delete (window as any).localStorage;
    cleanup();
  });

  it('uses default filter when localStorage is unavailable', async () => {
    render(<RemindersList />);
    const allButton = await screen.findByText(/^Все/);
    expect(allButton.className).toContain('bg-primary');
  });
});
