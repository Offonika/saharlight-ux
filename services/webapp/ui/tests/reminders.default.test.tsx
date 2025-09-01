import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, vi, afterEach, expect } from 'vitest';

afterEach(() => {
  vi.resetModules();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('default after meal minutes', () => {
  it('preselects profile default in RemindersCreate', async () => {
    vi.stubGlobal('Telegram', { WebApp: { platform: 'ios' } });
    vi.doMock('react-input-mask', () => ({
      default: ({ children, ...rest }: any) =>
        typeof children === 'function'
          ? children({ ...rest })
          : React.createElement('input', rest, children),
    }));
    vi.doMock('../src/features/reminders/api/reminders', () => ({
      useRemindersApi: () => ({ remindersPost: vi.fn() }),
    }));
    vi.doMock('../src/shared/toast', () => ({
      useToast: () => ({ success: vi.fn(), error: vi.fn() }),
    }));
    vi.doMock('../src/hooks/useTelegram', () => ({
      useTelegram: () => ({ user: { id: 1 }, sendData: vi.fn() }),
    }));
    vi.doMock('../src/hooks/useTelegramInitData', () => ({
      useTelegramInitData: () => null,
    }));
    vi.doMock('../src/features/profile/hooks', () => ({
      useDefaultAfterMealMinutes: () => 150,
    }));
    vi.doMock('../src/features/reminders/logic/validate', () => ({
      validate: () => ({}),
      hasErrors: () => false,
    }));
    vi.doMock('react-router-dom', () => ({
      useNavigate: () => vi.fn(),
    }));

    const { default: RemindersCreate } = await import(
      '../src/features/reminders/pages/RemindersCreate'
    );
    const { container, getByText } = render(
      React.createElement(RemindersCreate),
    );
    fireEvent.click(getByText('После события'));
    await waitFor(() => {
      const input = container.querySelector(
        'input[type="number"]',
      ) as HTMLInputElement;
      expect(input.value).toBe('150');
    });
    getByText('150 мин');
  });

  it('uses profile default in Templates', async () => {
    vi.doMock('../src/features/reminders/api/reminders', () => ({
      useRemindersApi: () => ({ remindersPost: vi.fn() }),
    }));
    vi.doMock('../src/shared/toast', () => ({
      useToast: () => ({ success: vi.fn(), error: vi.fn() }),
    }));
    vi.doMock('../src/features/profile/hooks', () => ({
      useDefaultAfterMealMinutes: () => 110,
    }));
    vi.doMock('../src/api/mock-server', () => ({
      mockApi: {},
    }));

    const { Templates } = await import(
      '../src/features/reminders/components/Templates'
    );
    const { getByText } = render(
      React.createElement(Templates, { telegramId: 1, onCreated: vi.fn() }),
    );
    getByText('После еды 110 мин');
  });
});

