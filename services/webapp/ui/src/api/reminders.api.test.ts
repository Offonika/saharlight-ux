import { describe, it, expect, vi, afterEach } from 'vitest';
import { ResponseError } from '@sdk/runtime';

const mockApiRemindersRemindersGet = vi.hoisted(() => vi.fn());
const mockApiRemindersPostRemindersPost = vi.hoisted(() => vi.fn());
const mockApiRemindersRemindersPatch = vi.hoisted(() => vi.fn());
const mockApiRemindersRemindersDelete = vi.hoisted(() => vi.fn());
const mockInstanceOfReminder = vi.hoisted(() => vi.fn());

vi.mock(
  '@sdk',
  () => ({
    DefaultApi: vi.fn(() => ({
      apiRemindersRemindersGet: mockApiRemindersRemindersGet,
      apiRemindersPostRemindersPost: mockApiRemindersPostRemindersPost,
      apiRemindersRemindersPatch: mockApiRemindersRemindersPatch,
      apiRemindersRemindersDelete: mockApiRemindersRemindersDelete,
    })),
  }),
  { virtual: true },
);

vi.mock(
  '@sdk/models',
  () => ({
    instanceOfReminder: mockInstanceOfReminder,
  }),
  { virtual: true },
);

import {
  getReminder,
  getReminders,
  createReminder,
  updateReminder,
  deleteReminder,
} from './reminders';

afterEach(() => {
  mockApiRemindersRemindersGet.mockReset();
  mockApiRemindersPostRemindersPost.mockReset();
  mockApiRemindersRemindersPatch.mockReset();
  mockApiRemindersRemindersDelete.mockReset();
  mockInstanceOfReminder.mockReset();
});

describe('getReminder', () => {
  it('throws on invalid API response', async () => {
    mockApiRemindersRemindersGet.mockResolvedValueOnce([]);
    await expect(getReminder(1, 1)).rejects.toThrow('Некорректный ответ API');
  });

  it('returns null on 404 response', async () => {
    mockApiRemindersRemindersGet.mockRejectedValueOnce(
      new ResponseError(new Response(null, { status: 404 })),
    );
    await expect(getReminder(1, 1)).resolves.toBeNull();
  });

  it('passes signal to API', async () => {
    const controller = new AbortController();
    mockApiRemindersRemindersGet.mockResolvedValueOnce({} as any);
    mockInstanceOfReminder.mockReturnValueOnce(true);
    await getReminder(1, 1, controller.signal);
    expect(mockApiRemindersRemindersGet).toHaveBeenCalledWith(
      { telegramId: 1, id: 1 },
      { signal: controller.signal },
    );
  });

  it('rethrows AbortError', async () => {
    const controller = new AbortController();
    const abortErr = new DOMException('Aborted', 'AbortError');
    mockApiRemindersRemindersGet.mockRejectedValueOnce(abortErr);
    await expect(getReminder(1, 1, controller.signal)).rejects.toBe(abortErr);
  });
});

describe('getReminders', () => {
  it('passes signal to API', async () => {
    const controller = new AbortController();
    mockApiRemindersRemindersGet.mockResolvedValueOnce([]);
    await getReminders(1, controller.signal);
    expect(mockApiRemindersRemindersGet).toHaveBeenCalledWith(
      { telegramId: 1 },
      { signal: controller.signal },
    );
  });

  it('rethrows AbortError', async () => {
    const controller = new AbortController();
    const abortErr = new DOMException('Aborted', 'AbortError');
    mockApiRemindersRemindersGet.mockRejectedValueOnce(abortErr);
    await expect(getReminders(1, controller.signal)).rejects.toBe(abortErr);
  });
});

describe('createReminder', () => {
  it('returns API response on success', async () => {
    const reminder = { id: 1 } as any;
    const apiResponse = { ok: true } as any;
    mockApiRemindersPostRemindersPost.mockResolvedValueOnce(apiResponse);
    await expect(createReminder(reminder)).resolves.toBe(apiResponse);
    expect(mockApiRemindersPostRemindersPost).toHaveBeenCalledWith({ reminder });
  });

  it('rethrows API errors', async () => {
    const error = new Error('api error');
    mockApiRemindersPostRemindersPost.mockRejectedValueOnce(error);
    await expect(createReminder({} as any)).rejects.toBe(error);
  });
});

describe('updateReminder', () => {
  it('returns API response on success', async () => {
    const reminder = { id: 1 } as any;
    const apiResponse = { ok: true } as any;
    mockApiRemindersRemindersPatch.mockResolvedValueOnce(apiResponse);
    await expect(updateReminder(reminder)).resolves.toBe(apiResponse);
    expect(mockApiRemindersRemindersPatch).toHaveBeenCalledWith({ reminder });
  });

  it('rethrows API errors', async () => {
    const error = new Error('api error');
    mockApiRemindersRemindersPatch.mockRejectedValueOnce(error);
    await expect(updateReminder({} as any)).rejects.toBe(error);
  });
});

describe('deleteReminder', () => {
  it('returns API response on success', async () => {
    const apiResponse = { ok: true } as any;
    mockApiRemindersRemindersDelete.mockResolvedValueOnce(apiResponse);
    await expect(deleteReminder(1, 2)).resolves.toBe(apiResponse);
    expect(mockApiRemindersRemindersDelete).toHaveBeenCalledWith({ telegramId: 1, id: 2 });
  });

  it('rethrows API errors', async () => {
    const error = new Error('api error');
    mockApiRemindersRemindersDelete.mockRejectedValueOnce(error);
    await expect(deleteReminder(1, 2)).rejects.toBe(error);
  });
});
