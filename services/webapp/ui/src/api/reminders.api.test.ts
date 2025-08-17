import { describe, it, expect, vi } from 'vitest';

const mockRemindersGet = vi.hoisted(() => vi.fn());

vi.mock('@sdk', () => ({
  DefaultApi: vi.fn(() => ({ remindersGet: mockRemindersGet })),
  instanceOfReminder: vi.fn(),
}));

import { getReminder } from './reminders';

describe('getReminder', () => {
  it('throws on invalid API response', async () => {
    mockRemindersGet.mockResolvedValueOnce([]);
    await expect(getReminder(1, 1)).rejects.toThrow('Некорректный ответ API');
  });
});
