import { describe, it, expect } from "vitest";
import { parseProfile, shouldWarnProfile } from "../src/pages/Profile";

describe("parseProfile", () => {
  it("returns parsed numbers for valid input", () => {
    const result = parseProfile({
      icr: "1",
      cf: "2",
      target: "5",
      low: "4",
      high: "10",
    });
    expect(result).toEqual({ icr: 1, cf: 2, target: 5, low: 4, high: 10 });
  });

  it("parses values with commas", () => {
    const result = parseProfile({
      icr: "1,5",
      cf: "2,5",
      target: "5,5",
      low: "4,0",
      high: "10,0",
    });
    expect(result).toEqual({ icr: 1.5, cf: 2.5, target: 5.5, low: 4, high: 10 });
  });

  it("returns null when any value is non-positive or invalid", () => {
    expect(
      parseProfile({ icr: "0", cf: "2", target: "5", low: "4", high: "10" }),
    ).toBeNull();
    expect(
      parseProfile({ icr: "1", cf: "-1", target: "5", low: "4", high: "10" }),
    ).toBeNull();
    expect(
      parseProfile({ icr: "a", cf: "2", target: "5", low: "4", high: "10" }),
    ).toBeNull();
  });

  it("returns null when low/high bounds are invalid", () => {
    expect(
      parseProfile({ icr: "1", cf: "2", target: "5", low: "8", high: "6" }),
    ).toBeNull();
    expect(
      parseProfile({ icr: "1", cf: "2", target: "3", low: "4", high: "10" }),
    ).toBeNull();
    expect(
      parseProfile({ icr: "1", cf: "2", target: "12", low: "4", high: "10" }),
    ).toBeNull();
  });

  it("detects suspicious profile values", () => {
    expect(
      shouldWarnProfile({ icr: 9, cf: 2, target: 5, low: 4, high: 10 }),
    ).toBe(true);
    expect(
      shouldWarnProfile({ icr: 8, cf: 2, target: 5, low: 4, high: 10 }),
    ).toBe(false);
    expect(
      shouldWarnProfile({ icr: 9, cf: 3, target: 5, low: 4, high: 10 }),
    ).toBe(false);
  });
});
