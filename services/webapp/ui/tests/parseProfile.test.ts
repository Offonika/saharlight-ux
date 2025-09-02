import { describe, it, expect } from "vitest";
import { parseProfile, shouldWarnProfile } from "../src/pages/Profile";
import type { RapidInsulin } from "../src/features/profile/api";

type TestProfileForm = {
  icr: string;
  cf: string;
  target: string;
  low: string;
  high: string;
  timezone: string;
  timezoneAuto: boolean;
  dia: string;
  preBolus: string;
  roundStep: string;
  carbUnit: "g" | "xe";
  gramsPerXe: string;
  rapidInsulinType: RapidInsulin;
  maxBolus: string;
  afterMealMinutes: string;
};

const makeProfile = (
  overrides: Partial<TestProfileForm> = {},
): TestProfileForm => ({
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

  it("skips gramsPerXe validation when carb unit is grams", () => {
    const result = parseProfile(makeProfile({ gramsPerXe: "", carbUnit: "g" }));
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
      gramsPerXe: 0,
      rapidInsulinType: "lispro",
      maxBolus: 20,
      afterMealMinutes: 60,
    });
  });

  it("validates gramsPerXe when carb unit is XE", () => {
    const result = parseProfile(
      makeProfile({ gramsPerXe: "", carbUnit: "xe" }),
    );
    expect(result).toBeNull();
  });

  it("returns null when low/high bounds are invalid", () => {
    expect(parseProfile(makeProfile({ low: "8", high: "6" }))).toBeNull();
    expect(parseProfile(makeProfile({ target: "3" }))).toBeNull();
    expect(parseProfile(makeProfile({ target: "12" }))).toBeNull();
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
    expect(result).toEqual({
      icr: 0,
      cf: 0,
      target: 5,
      low: 4,
      high: 10,
      dia: 0,
      preBolus: 0,
      roundStep: 1,
      carbUnit: "g",
      gramsPerXe: 12,
      rapidInsulinType: "lispro",
      maxBolus: 0,
      afterMealMinutes: 60,
    });
  });

  it("parses none therapy profile skipping insulin fields", () => {
    const result = parseProfile(
      makeProfile({
        icr: "",
        cf: "",
        dia: "",
        preBolus: "",
        maxBolus: "",
      }),
      "none",
    );
    expect(result).toEqual({
      icr: 0,
      cf: 0,
      target: 5,
      low: 4,
      high: 10,
      dia: 0,
      preBolus: 0,
      roundStep: 1,
      carbUnit: "g",
      gramsPerXe: 12,
      rapidInsulinType: "lispro",
      maxBolus: 0,
      afterMealMinutes: 60,
    });
  });

  it("validates required fields for tablet therapy", () => {
    expect(
      parseProfile(
        makeProfile({
          icr: "",
          cf: "",
          dia: "",
          preBolus: "",
          maxBolus: "",
          low: "8",
          high: "6",
        }),
        "tablets",
      ),
    ).toBeNull();
  });

  it("validates required fields for none therapy", () => {
    expect(
      parseProfile(
        makeProfile({
          icr: "",
          cf: "",
          dia: "",
          preBolus: "",
          maxBolus: "",
          target: "3",
        }),
        "none",
      ),
    ).toBeNull();
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
        rapidInsulinType: "aspart",
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
        rapidInsulinType: "aspart",
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
        rapidInsulinType: "aspart",
        maxBolus: 1,
        afterMealMinutes: 0,
      }),
    ).toBe(false);
  });
});
