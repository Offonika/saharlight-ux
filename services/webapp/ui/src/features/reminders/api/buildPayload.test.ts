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
      telegram_id: 1,
      type: 'sugar',
      is_enabled: true,
      time: '09:00',
    });
    expect('interval_hours' in payload).toBe(false);
    expect('minutes_after' in payload).toBe(false);
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
      telegram_id: 2,
      type: 'insulin_short',
      is_enabled: false,
      interval_hours: 0.5,
    });
    expect('time' in payload).toBe(false);
    expect('minutes_after' in payload).toBe(false);
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
      telegram_id: 3,
      type: 'meal',
      is_enabled: true,
      minutes_after: 15,
    });
    expect('time' in payload).toBe(false);
    expect('interval_hours' in payload).toBe(false);
  });
});
