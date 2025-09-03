import type { ProfileSchema, ProfileSettingsIn } from "@sdk";

export type RapidInsulin = "aspart" | "lispro" | "glulisine" | "regular";

export interface Profile extends ProfileSchema {
  dia?: number | null;
  preBolus?: number | null;
  roundStep?: number | null;
  carbUnits?: "g" | "xe" | null;
  gramsPerXe?: number | null;
  rapidInsulinType?: RapidInsulin | null;
  maxBolus?: number | null;
  afterMealMinutes?: number | null;
  therapyType?: "insulin" | "tablets" | "none" | "mixed" | null;
}

export type PatchProfileDto = Partial<
  Pick<
    ProfileSettingsIn,
    | "timezone"
    | "timezoneAuto"
    | "dia"
    | "preBolus"
    | "roundStep"
    | "carbUnits"
    | "gramsPerXe"
    | "rapidInsulinType"
    | "maxBolus"
    | "afterMealMinutes"
    | "therapyType"
  >
>;

