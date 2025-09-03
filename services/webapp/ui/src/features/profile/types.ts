import type { ProfileSchema } from "@sdk";

export type RapidInsulin = "aspart" | "lispro" | "glulisine" | "regular";

export interface Profile extends ProfileSchema {
  dia?: number | null;
  preBolus?: number | null;
  roundStep?: number | null;
  carbUnit?: "g" | "xe" | null;
  gramsPerXe?: number | null;
  rapidInsulinType?: RapidInsulin | null;
  maxBolus?: number | null;
  afterMealMinutes?: number | null;
  therapyType?: "insulin" | "tablets" | "none" | "mixed" | null;
}

export type PatchProfileDto = {
  timezone?: string | null;
  timezoneAuto?: boolean | null;
  dia?: number | null;
  preBolus?: number | null;
  roundStep?: number | null;
  carbUnit?: "g" | "xe" | null;
  gramsPerXe?: number | null;
  rapidInsulinType?: RapidInsulin | null;
  maxBolus?: number | null;
  afterMealMinutes?: number | null;
  therapyType?: "insulin" | "tablets" | "none" | "mixed" | null;
};

