import { describe, it, expect } from "vitest";
import { parseProfile, shouldWarnProfile } from "../src/pages/Profile";
import type { RapidInsulin } from "../src/features/profile/types";

const makeProfile = (
  overrides: Record<string, string | boolean | RapidInsulin> = {},
) => ({
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
  carbUnits: "g",
  gramsPerXe: "12",
  rapidInsulinType: "lispro" as RapidInsulin,
  maxBolus: "20",
  afterMealMinutes: "60",
  ...overrides,
});

describe("parseProfile", () => {
  it("returns data and no errors for valid input", () => {
    const result = parseProfile(makeProfile());
    expect(result.errors).toEqual({});
    expect(result.data).toEqual({
      icr: 1,
      cf: 2,
      target: 5,
      low: 4,
      high: 10,
      dia: 7,
      preBolus: 10,
      roundStep: 1,
      carbUnits: "g",
      gramsPerXe: 12,
      rapidInsulinType: "lispro" as RapidInsulin,
      maxBolus: 20,
      afterMealMinutes: 60,
    });
  });

  it("reports errors for invalid or missing values", () => {
    expect(parseProfile(makeProfile({ icr: "0" })).errors.icr).toBe(
      "out_of_range",
    );
    expect(parseProfile(makeProfile({ cf: "abc" })).errors.cf).toBe(
      "invalid",
    );
  });

  it("parses comma decimal numbers", () => {
    const result = parseProfile(
      makeProfile({ icr: "1,5", cf: "2,5", target: "5,5" }),
    );
    expect(result.errors).toEqual({});
    expect(result.data.icr).toBeCloseTo(1.5);
    expect(result.data.cf).toBeCloseTo(2.5);
    expect(result.data.target).toBeCloseTo(5.5);
  });

  it("requires gramsPerXe when carbUnits is XE", () => {
    const result = parseProfile(
      makeProfile({ gramsPerXe: "", carbUnits: "xe" }),
    );
    expect(result.errors.gramsPerXe).toBe("required");
  });

  it("does not set zero for empty optional numbers", () => {
    const result = parseProfile(makeProfile({ gramsPerXe: "" }));
    expect(result.errors).toEqual({});
    expect(result.data.gramsPerXe).toBeUndefined();
  });

  it("leaves empty required numbers undefined", () => {
    const result = parseProfile(makeProfile({ icr: "" }));
    expect(result.errors.icr).toBe("required");
    expect(result.data.icr).toBeUndefined();
  });

  it("validates target range", () => {
    const result = parseProfile(makeProfile({ target: "12" }));
    expect(result.errors.target).toBe("out_of_range");
  });

  it("parses tablet therapy profile skipping insulin fields", () => {
    const result = parseProfile(
      makeProfile({
        icr: "",
        cf: "",
        dia: "",
        preBolus: "",
        maxBolus: "",
      }),
      "tablets",
    );
    expect(result.errors).toEqual({});
    expect(result.data.icr).toBe(0);
    expect(result.data.cf).toBe(0);
    expect(result.data.rapidInsulinType).toBeUndefined();
  });
});

describe("shouldWarnProfile", () => {
  it("warns when ICR is high and CF is low", () => {
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
        carbUnits: "g",
        gramsPerXe: 10,
        rapidInsulinType: "aspart" as RapidInsulin,
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
        carbUnits: "g",
        gramsPerXe: 10,
        rapidInsulinType: "aspart" as RapidInsulin,
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
        carbUnits: "g",
        gramsPerXe: 10,
        rapidInsulinType: "aspart" as RapidInsulin,
        maxBolus: 1,
        afterMealMinutes: 0,
      }),
    ).toBe(false);
  });

  it("warns when DIA exceeds 12", () => {
    expect(
      shouldWarnProfile({
        icr: 1,
        cf: 2,
        target: 5,
        low: 4,
        high: 10,
        dia: 13,
        preBolus: 0,
        roundStep: 1,
        carbUnits: "g",
        gramsPerXe: 10,
        rapidInsulinType: "aspart" as RapidInsulin,
        maxBolus: 1,
        afterMealMinutes: 0,
      }),
    ).toBe(true);

    expect(
      shouldWarnProfile({
        icr: 1,
        cf: 2,
        target: 5,
        low: 4,
        high: 10,
        dia: 12,
        preBolus: 0,
        roundStep: 1,
        carbUnits: "g",
        gramsPerXe: 10,
        rapidInsulinType: "aspart" as RapidInsulin,
        maxBolus: 1,
        afterMealMinutes: 0,
      }),
    ).toBe(false);
  });

  it("warns when carbUnits change without ICR recalculation", () => {
    const original = {
      icr: 10,
      cf: 2,
      target: 5,
      low: 4,
      high: 10,
      dia: 1,
      preBolus: 0,
      roundStep: 1,
      carbUnits: "g" as const,
      gramsPerXe: 12,
      rapidInsulinType: "aspart" as RapidInsulin,
      maxBolus: 1,
      afterMealMinutes: 0,
    };

    expect(
      shouldWarnProfile({ ...original, carbUnits: "xe" }, original),
    ).toBe(true);

    expect(
      shouldWarnProfile({ ...original, carbUnits: "xe", icr: 0.8 }, original),
    ).toBe(false);
  });

  it("does not warn for non-insulin therapy", () => {
    expect(
      shouldWarnProfile({
        icr: 0,
        cf: 0,
        target: 5,
        low: 4,
        high: 10,
        dia: 0,
        preBolus: 0,
        roundStep: 1,
        carbUnits: "g",
        gramsPerXe: 10,
        rapidInsulinType: "aspart" as RapidInsulin,
        maxBolus: 0,
        afterMealMinutes: 0,
      }),
    ).toBe(false);
  });
});

