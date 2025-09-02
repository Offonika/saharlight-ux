import { describe, it, expect } from "vitest";
import { validate } from "./validate";
import type { ReminderDto } from "../types";

describe("validate", () => {
  const base: ReminderDto = {
    telegramId: 1,
    type: "sugar",
    kind: "at_time",
    time: "07:30",
    isEnabled: true,
  };

  it("accepts valid HH:MM time", () => {
    const errors = validate(base);
    expect(errors.time).toBeUndefined();
  });

  it("rejects invalid time format", () => {
    const errors = validate({ ...base, time: "7:30" });
    expect(errors.time).toBe("Формат HH:MM");
  });

  const afterBase: ReminderDto = {
    telegramId: 1,
    type: "after_meal",
    kind: "after_event",
    minutesAfter: 60,
    isEnabled: true,
  };

  it("accepts valid minutesAfter", () => {
    const errors = validate(afterBase);
    expect(errors.minutesAfter).toBeUndefined();
  });

  it("rejects minutesAfter below minimum", () => {
    const errors = validate({ ...afterBase, minutesAfter: 3 });
    expect(errors.minutesAfter).toBe("Минуты 5..480");
  });

  it("rejects minutesAfter above maximum", () => {
    const errors = validate({ ...afterBase, minutesAfter: 500 });
    expect(errors.minutesAfter).toBe("Минуты 5..480");
  });

  it("rejects minutesAfter not divisible by 5", () => {
    const errors = validate({ ...afterBase, minutesAfter: 7 });
    expect(errors.minutesAfter).toBe("Кратно 5");
  });
});
