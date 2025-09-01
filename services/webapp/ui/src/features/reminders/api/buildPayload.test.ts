import { describe, expect, it } from "vitest";
import { buildReminderPayload } from "./buildPayload";

import type { ReminderFormValues } from "./buildPayload";

describe("buildReminderPayload", () => {
  it("omits daysOfWeek for after_event reminders", () => {
    const input: ReminderFormValues = {
      telegramId: 1,
      type: "after_meal",
      kind: "after_event",
      minutesAfter: 15,
      daysOfWeek: [1, 2, 3],
    };

    const result = buildReminderPayload(input);

    expect(result).toHaveProperty("minutesAfter", 15);
    expect(result).not.toHaveProperty("daysOfWeek");
  });
});

