import { describe, it, expect, vi, afterEach } from 'vitest';
import { ResponseError, Configuration } from '@offonika/diabetes-ts-sdk/runtime';

const mockRemindersGet = vi.hoisted(() => vi.fn());
const mockRemindersIdGet = vi.hoisted(() => vi.fn());
const mockRemindersPost = vi.hoisted(() => vi.fn());
const mockRemindersPatch = vi.hoisted(() => vi.fn());
const mockRemindersDelete = vi.hoisted(() => vi.fn());
const mockInstanceOfReminder = vi.hoisted(() => vi.fn());

vi.mock(
  '@offonika/diabetes-ts-sdk/runtime',
  () => ({
    ResponseError: class extends Error {
      response: Response;
      constructor(response: Response) {
        super('ResponseError');
        this.response = response;
      }
    },
    Configuration: class {},
  }),
  { virtual: true },
);

vi.mock(
  '@offonika/diabetes-ts-sdk',
  () => ({
    RemindersApi: vi.fn(() => ({
      remindersGet: mockRemindersGet,
      remindersIdGet: mockRemindersIdGet,
      remindersPost: mockRemindersPost,
      remindersPatch: mockRemindersPatch,
      remindersDelete: mockRemindersDelete,
    })),
    Configuration,
  }),
  { virtual: true },
);

vi.mock(
  '@offonika/diabetes-ts-sdk/models',
  () => ({
    instanceOfReminderSchema: mockInstanceOfReminder,
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
  mockRemindersGet.mockReset();
  mockRemindersIdGet.mockReset();
  mockRemindersPost.mockReset();
  mockRemindersPatch.mockReset();
  mockRemindersDelete.mockReset();
  mockInstanceOfReminder.mockReset();
});

describe('getReminder', () => {
  it('throws on invalid API response', async () => {
    mockRemindersIdGet.mockResolvedValueOnce({});
    await expect(getReminder(1, 1)).rejects.toThrow('Некорректный ответ API');
  });

  it('returns null on 404 response', async () => {
    mockRemindersIdGet.mockRejectedValueOnce(
      new ResponseError(new Response(null, { status: 404 })),
    );
    await expect(getReminder(1, 1)).resolves.toBeNull();
  });

  it('passes signal to API', async () => {
    const controller = new AbortController();
    mockRemindersIdGet.mockResolvedValueOnce({} as any);
    mockInstanceOfReminder.mockReturnValueOnce(true);
    await getReminder(1, 1, controller.signal);
    expect(mockRemindersIdGet).toHaveBeenCalledWith(
      { telegramId: 1, id: 1 },
      { signal: controller.signal },
    );
  });

  it('rethrows AbortError', async () => {
    const controller = new AbortController();
    const abortErr = new DOMException('Aborted', 'AbortError');
    mockRemindersIdGet.mockRejectedValueOnce(abortErr);
    await expect(getReminder(1, 1, controller.signal)).rejects.toBe(abortErr);
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

  it('throws on invalid API response', async () => {
    mockRemindersGet.mockResolvedValueOnce([{} as any]);
    mockInstanceOfReminder.mockReturnValueOnce(false);
    await expect(getReminders(1)).rejects.toThrow('Некорректный ответ API');
  });

  it('returns empty array on 404 response', async () => {
    mockRemindersGet.mockRejectedValueOnce(
      new ResponseError(new Response(null, { status: 404 })),
    );
    await expect(getReminders(1)).resolves.toEqual([]);
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
