import { describe, it, expect, vi, afterEach } from 'vitest';
import { ResponseError } from '@sdk/runtime';

const mockRemindersGet = vi.hoisted(() => vi.fn());

vi.mock('@sdk', () => ({
  DefaultApi: vi.fn(() => ({ remindersGet: mockRemindersGet })),
  instanceOfReminder: vi.fn(),
}));

import { getReminder, getReminders } from './reminders';

afterEach(() => {
  mockRemindersGet.mockReset();
});

describe('getReminder', () => {
  it('throws on invalid API response', async () => {
    mockRemindersGet.mockResolvedValueOnce([]);
    await expect(getReminder(1, 1)).rejects.toThrow('Некорректный ответ API');
  });

  it('returns null on 404 response', async () => {
    mockRemindersGet.mockRejectedValueOnce(
      new ResponseError(new Response(null, { status: 404 })),
    );
    await expect(getReminder(1, 1)).resolves.toBeNull();
  });
});

describe('getReminders', () => {
  it('passes signal to API', async () => {
    const controller = new AbortController();
    mockRemindersGet.mockResolvedValueOnce([]);
    await getReminders(1, controller.signal);
    expect(mockRemindersGet).toHaveBeenCalledWith(
      { telegramId: 1 },
      { signal: controller.signal },
    );
  });

  it('rethrows AbortError', async () => {
    const controller = new AbortController();
    const abortErr = new DOMException('Aborted', 'AbortError');
    mockRemindersGet.mockRejectedValueOnce(abortErr);
    await expect(getReminders(1, controller.signal)).rejects.toBe(abortErr);
  });
});
