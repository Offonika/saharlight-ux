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
      carbUnits: "g",
      gramsPerXe: 12,
      rapidInsulinType: "lispro" as RapidInsulin,
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

  it("skips gramsPerXe validation when carbUnits is grams", () => {
    const result = parseProfile(makeProfile({ gramsPerXe: "", carbUnits: "g" }));
    expect(result).toEqual({
      icr: 1,
      cf: 2,
      target: 5,
      low: 4,
      high: 10,
      dia: 7,
      preBolus: 10,
      roundStep: 1,
      carbUnits: "g",
      gramsPerXe: 0,
      rapidInsulinType: "lispro" as RapidInsulin,
      maxBolus: 20,
      afterMealMinutes: 60,
    });
  });

  it("validates gramsPerXe when carbUnits is XE", () => {
    const result = parseProfile(
      makeProfile({ gramsPerXe: "", carbUnits: "xe" }),
    );
    expect(result).toBeNull();
  });

  it("returns null when low/high bounds are invalid", () => {
    expect(parseProfile(makeProfile({ low: "8", high: "6" }))).toBeNull();
    expect(parseProfile(makeProfile({ target: "3" }))).toBeNull();
    expect(parseProfile(makeProfile({ target: "12" }))).toBeNull();
  });

  it("validates preBolus upper bound", () => {
    expect(parseProfile(makeProfile({ preBolus: "61" }))).toBeNull();
    expect(parseProfile(makeProfile({ preBolus: "60" }))?.preBolus).toBe(60);
  });

  it("validates DIA upper bound", () => {
    expect(parseProfile(makeProfile({ dia: "25" }))).toBeNull();
    expect(parseProfile(makeProfile({ dia: "24" }))?.dia).toBe(24);
  });

  it("validates afterMealMinutes upper bound", () => {
    expect(
      parseProfile(makeProfile({ afterMealMinutes: "241" })),
    ).toBeNull();
    expect(
      parseProfile(makeProfile({ afterMealMinutes: "240" }))?.afterMealMinutes,
    ).toBe(240);
  });

  it("allows large roundStep and maxBolus", () => {
    const result = parseProfile(
      makeProfile({ roundStep: "10", maxBolus: "50" }),
    );
    expect(result?.roundStep).toBe(10);
    expect(result?.maxBolus).toBe(50);
  });

  it("allows gramsPerXe above 20", () => {
    const result = parseProfile(
      makeProfile({ gramsPerXe: "25", carbUnits: "xe" }),
    );
    expect(result?.gramsPerXe).toBe(25);
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
      carbUnits: "g",
      gramsPerXe: 12,
      rapidInsulinType: "lispro" as RapidInsulin,
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
      carbUnits: "g",
      gramsPerXe: 12,
      rapidInsulinType: "lispro" as RapidInsulin,
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

  it("parses mixed therapy profile including insulin fields", () => {
    const result = parseProfile(makeProfile(), "mixed");
    expect(result).toEqual({
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
