import { describe, it, expect } from 'vitest';
import { buildReminderPayload, ReminderFormValues } from './buildPayload';

const base: ReminderFormValues = {
  telegramId: 1,
  type: 'sugar',
  kind: 'at_time',
  time: '09:00',
};

describe('buildReminderPayload', () => {
  it('builds payload for at_time with generated title', () => {
    const payload = buildReminderPayload(base);
    expect(payload).toEqual({
      telegramId: 1,
      type: 'sugar',
      kind: 'at_time',
      time: '09:00',
      daysOfWeek: undefined,
      isEnabled: true,
      title: 'Измерение сахара · 09:00',
    });
    expect('intervalMinutes' in payload).toBe(false);
    expect('minutesAfter' in payload).toBe(false);
  });

  it('builds payload for every with intervalMinutes', () => {
    const payload = buildReminderPayload({
      telegramId: 2,
      type: 'insulin_short',
      kind: 'every',
      intervalMinutes: 30,
      daysOfWeek: [1, 3],
      isEnabled: false,
    });
    expect(payload).toEqual({
      telegramId: 2,
      type: 'insulin_short',
      kind: 'every',
      intervalMinutes: 30,
      daysOfWeek: [1, 3],
      isEnabled: false,
      title: 'Инсулин (короткий) · каждые 30 мин',
    });
    expect('time' in payload).toBe(false);
    expect('minutesAfter' in payload).toBe(false);
  });

  it('uses custom title and minutesAfter for after_event', () => {
    const payload = buildReminderPayload({
      telegramId: 3,
      type: 'meal',
      kind: 'after_event',
      minutesAfter: 15,
      title: '  My title  ',
    });
    expect(payload).toEqual({
      telegramId: 3,
      type: 'meal',
      kind: 'after_event',
      minutesAfter: 15,
      daysOfWeek: undefined,
      isEnabled: true,
      title: 'My title',
    });
    expect('time' in payload).toBe(false);
    expect('intervalMinutes' in payload).toBe(false);
  });
});
