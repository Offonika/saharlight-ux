import { describe, it, expect, vi, afterEach } from 'vitest';
import { ResponseError } from '@sdk/runtime';

const mockRemindersGet = vi.hoisted(() => vi.fn());
const mockRemindersPost = vi.hoisted(() => vi.fn());
const mockRemindersPatch = vi.hoisted(() => vi.fn());
const mockRemindersDelete = vi.hoisted(() => vi.fn());

vi.mock('@sdk', () => ({
  DefaultApi: vi.fn(() => ({
    remindersGet: mockRemindersGet,
    remindersPost: mockRemindersPost,
    remindersPatch: mockRemindersPatch,
    remindersDelete: mockRemindersDelete,
  })),
  instanceOfReminder: vi.fn(),
}), { virtual: true });

import {
  getReminder,
  getReminders,
  createReminder,
  updateReminder,
  deleteReminder,
} from './reminders';

afterEach(() => {
  mockRemindersGet.mockReset();
  mockRemindersPost.mockReset();
  mockRemindersPatch.mockReset();
  mockRemindersDelete.mockReset();
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

describe('createReminder', () => {
  it('returns API response on success', async () => {
    const reminder = { id: 1 } as any;
    const apiResponse = { ok: true } as any;
    mockRemindersPost.mockResolvedValueOnce(apiResponse);
    await expect(createReminder(reminder)).resolves.toBe(apiResponse);
    expect(mockRemindersPost).toHaveBeenCalledWith({ reminder });
  });

  it('rethrows API errors', async () => {
    const error = new Error('api error');
    mockRemindersPost.mockRejectedValueOnce(error);
    await expect(createReminder({} as any)).rejects.toBe(error);
  });
});

describe('updateReminder', () => {
  it('returns API response on success', async () => {
    const reminder = { id: 1 } as any;
    const apiResponse = { ok: true } as any;
    mockRemindersPatch.mockResolvedValueOnce(apiResponse);
    await expect(updateReminder(reminder)).resolves.toBe(apiResponse);
    expect(mockRemindersPatch).toHaveBeenCalledWith({ reminder });
  });

  it('rethrows API errors', async () => {
    const error = new Error('api error');
    mockRemindersPatch.mockRejectedValueOnce(error);
    await expect(updateReminder({} as any)).rejects.toBe(error);
  });
});

describe('deleteReminder', () => {
  it('returns API response on success', async () => {
    const apiResponse = { ok: true } as any;
    mockRemindersDelete.mockResolvedValueOnce(apiResponse);
    await expect(deleteReminder(1, 2)).resolves.toBe(apiResponse);
    expect(mockRemindersDelete).toHaveBeenCalledWith({ telegramId: 1, id: 2 });
  });

  it('rethrows API errors', async () => {
    const error = new Error('api error');
    mockRemindersDelete.mockRejectedValueOnce(error);
    await expect(deleteReminder(1, 2)).rejects.toBe(error);
  });
});
