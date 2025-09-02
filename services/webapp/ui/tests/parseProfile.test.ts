import { describe, it, expect } from "vitest";
import { parseProfile, shouldWarnProfile } from "../src/pages/Profile";

const makeProfile = (overrides: Record<string, string | boolean> = {}) => ({
  icr: "1",
  cf: "2",
  target: "5",
  low: "4",
  high: "10",
  timezone: "",
  timezoneAuto: false,
  dia: "7",
  preBolus: "10",
  roundStep: "1",
  carbUnit: "g",
  gramsPerXe: "12",
  rapidInsulinType: "lispro",
  maxBolus: "20",
  afterMealMinutes: "60",
  ...overrides,
});

describe("parseProfile", () => {
  it("returns parsed numbers for valid input", () => {
    const result = parseProfile(makeProfile());
    expect(result).toEqual({
      icr: 1,
      cf: 2,
      target: 5,
      low: 4,
      high: 10,
      dia: 7,
      preBolus: 10,
      roundStep: 1,
      carbUnit: "g",
      gramsPerXe: 12,
      rapidInsulinType: "lispro",
      maxBolus: 20,
      afterMealMinutes: 60,
    });
  });

  it("returns null when any value is non-positive or invalid", () => {
    expect(parseProfile(makeProfile({ icr: "0" }))).toBeNull();
    expect(parseProfile(makeProfile({ cf: "-1" }))).toBeNull();
    expect(parseProfile(makeProfile({ icr: "a" }))).toBeNull();
  });

  it("parses comma decimal numbers", () => {
    const result = parseProfile(
      makeProfile({ icr: "1,5", cf: "2,5", target: "5,5" }),
    );
    expect(result?.icr).toBe(1.5);
    expect(result?.cf).toBe(2.5);
    expect(result?.target).toBe(5.5);
  });

  it("returns null for multiple commas", () => {
    const result = parseProfile(makeProfile({ icr: "1,2,3" }));
    expect(result).toBeNull();
  });

  it("returns null when low/high bounds are invalid", () => {
    expect(parseProfile(makeProfile({ low: "8", high: "6" }))).toBeNull();
    expect(parseProfile(makeProfile({ target: "3" }))).toBeNull();
    expect(parseProfile(makeProfile({ target: "12" }))).toBeNull();
  });

  it("handles tablet therapy without insulin fields", () => {
    const result = parseProfile(
      makeProfile({
        icr: "",
        cf: "",
        target: "",
        low: "",
        high: "",
        dia: "",
        preBolus: "",
        roundStep: "",
        rapidInsulinType: "",
        maxBolus: "",
        afterMealMinutes: "",
      }),
      "tablets",
    );
    expect(result).toMatchObject({ carbUnit: "g", gramsPerXe: 12 });
  });

  it("handles none therapy without insulin fields", () => {
    const result = parseProfile(
      makeProfile({
        icr: "",
        cf: "",
        target: "",
        low: "",
        high: "",
        dia: "",
        preBolus: "",
        roundStep: "",
        rapidInsulinType: "",
        maxBolus: "",
        afterMealMinutes: "",
      }),
      "none",
    );
    expect(result).toMatchObject({ carbUnit: "g", gramsPerXe: 12 });
  });
});

describe("shouldWarnProfile", () => {
  it("detects suspicious profile values", () => {
    expect(
      shouldWarnProfile({
        icr: 9,
        cf: 2,
        target: 5,
        low: 4,
        high: 10,
        dia: 1,
        preBolus: 0,
        roundStep: 1,
        carbUnit: "g",
        gramsPerXe: 10,
        rapidInsulinType: "a",
        maxBolus: 1,
        afterMealMinutes: 0,
      }),
    ).toBe(true);
    expect(
      shouldWarnProfile({
        icr: 8,
        cf: 2,
        target: 5,
        low: 4,
        high: 10,
        dia: 1,
        preBolus: 0,
        roundStep: 1,
        carbUnit: "g",
        gramsPerXe: 10,
        rapidInsulinType: "a",
        maxBolus: 1,
        afterMealMinutes: 0,
      }),
    ).toBe(false);
    expect(
      shouldWarnProfile({
        icr: 9,
        cf: 3,
        target: 5,
        low: 4,
        high: 10,
        dia: 1,
        preBolus: 0,
        roundStep: 1,
        carbUnit: "g",
        gramsPerXe: 10,
        rapidInsulinType: "a",
        maxBolus: 1,
        afterMealMinutes: 0,
      }),
    ).toBe(false);
  });
});
