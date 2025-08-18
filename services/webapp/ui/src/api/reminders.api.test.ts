import { describe, it, expect, vi, afterEach } from 'vitest';
import { ResponseError } from '@sdk/runtime';

const mockRemindersGet = vi.hoisted(() => vi.fn());

vi.mock('@sdk', () => ({
  DefaultApi: vi.fn(() => ({ remindersGet: mockRemindersGet })),
  instanceOfReminder: vi.fn(),
}));

import { getReminder } from './reminders';

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
