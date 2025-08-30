import { afterEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { render, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { ReminderType } from '@sdk/models/ReminderType';

describe('RemindersApi', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('posts to /api/reminders and parses JSON', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), {
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', mockFetch);
    const { makeRemindersApi } = await import('../src/features/reminders/api/reminders');
    const api = makeRemindersApi(null);
    const result = await api.remindersPost({
      reminder: { telegramId: 1, type: ReminderType.Sugar },
    });
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/reminders',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(result).toEqual({ ok: true });
  });
});

describe('RemindersEdit', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('updates time via UI and persists', async () => {
    vi.resetModules();

    let backendReminder = {
      id: 1,
      telegramId: 1,
      type: ReminderType.Sugar,
      kind: 'at_time',
      time: '08:00',
      isEnabled: true,
      title: 'Test',
    };

    const remindersIdGet = vi
      .fn()
      .mockImplementation(() => Promise.resolve(backendReminder));
    const remindersPatch = vi.fn().mockImplementation(({ reminder }) => {
      backendReminder = { ...backendReminder, ...reminder };
      return Promise.resolve({});
    });

    vi.doMock('../src/features/reminders/api/reminders', () => ({
      useRemindersApi: () => ({ remindersIdGet, remindersPatch }),
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
    vi.doMock('react-router-dom', () => ({
      useNavigate: () => vi.fn(),
      useParams: () => ({ id: '1' }),
    }));

    const { default: RemindersEdit } = await import('../src/features/reminders/pages/RemindersEdit');
    const { container, getByText } = render(React.createElement(RemindersEdit));

    await waitFor(() => {
      const input = container.querySelector('input[type="time"]') as HTMLInputElement;
      expect(input.value).toBe('08:00');
    });

    const input = container.querySelector('input[type="time"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '09:30' } });
    fireEvent.click(getByText('Сохранить'));

    await waitFor(() => {
      expect(remindersPatch).toHaveBeenCalledWith({
        reminder: expect.objectContaining({ time: '09:30' }),
      });
    });

    await expect(
      remindersIdGet({ id: 1, telegramId: 1 }),
    ).resolves.toHaveProperty('time', '09:30');
  });
});
