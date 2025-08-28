import { describe, expect, test, vi } from 'vitest';
import { buildReminderPayload } from './buildPayload';
import { Configuration } from '@sdk/runtime.ts';
import { RemindersApi } from '@sdk/apis';
import { mockApi } from '../../../api/mock-server';

describe('reminders api', () => {
  test('builds camelCase payload and posts without mock fallback', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    // @ts-expect-error - override global fetch for test
    global.fetch = fetchMock;

    const createReminderSpy = vi.spyOn(mockApi, 'createReminder').mockResolvedValue({});

    const cfg = new Configuration({ basePath: '', fetchApi: fetchMock });
    const api = new RemindersApi(cfg);

    const form = {
      telegramId: 1,
      type: 'sugar',
      kind: 'at_time' as const,
      time: '07:30',
      isEnabled: true,
    };

    const payload = buildReminderPayload(form);
    expect(payload).toEqual({
      telegramId: 1,
      type: 'sugar',
      isEnabled: true,
      time: '07:30',
    });

    try {
      await api.remindersPost({ reminder: payload });
    } catch (err) {
      await mockApi.createReminder(payload);
    }

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0][0]).toBe('/reminders');
    const body = fetchMock.mock.calls[0][1]?.body as string;
    expect(body).toContain('"telegramId"');
    expect(createReminderSpy).not.toHaveBeenCalled();
  });
});
