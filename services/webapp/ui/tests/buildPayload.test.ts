import { describe, it, expect } from "vitest";
import { buildReminderPayload } from "../src/features/reminders/api/buildPayload";

describe("buildReminderPayload daysOfWeek handling", () => {
  it("omits daysOfWeek for after_event", () => {
    const payload = buildReminderPayload({
      telegramId: 1,
      type: "after_meal",
      kind: "after_event",
      minutesAfter: 30,
      daysOfWeek: [1, 2, 3],
    });
    expect(payload.daysOfWeek).toBeUndefined();
  });

  it("includes daysOfWeek for regular kinds", () => {
    const payload = buildReminderPayload({
      telegramId: 1,
      type: "sugar",
      kind: "at_time",
      time: "08:00",
      daysOfWeek: [1, 2],
    });
    expect(payload.daysOfWeek).toEqual(new Set([1, 2]));
  });
});
