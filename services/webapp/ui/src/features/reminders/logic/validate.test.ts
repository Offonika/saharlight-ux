import { describe, it, expect } from "vitest";
import { validate } from "./validate";
import type { ReminderFormValues } from "../api/buildPayload";

describe("validate", () => {
  const base: ReminderFormValues = {
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
});
