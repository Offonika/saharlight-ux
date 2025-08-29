import { afterEach, describe, expect, it, vi } from 'vitest';
import { makeRemindersApi } from '../src/features/reminders/api/reminders';
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
