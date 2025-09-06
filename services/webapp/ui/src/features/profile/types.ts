import type {
  ProfileSchema,
  ProfileSettingsIn,
  ProfileSettingsOut,
} from "@sdk";

export type RapidInsulin = "aspart" | "lispro" | "glulisine" | "regular";

export type Profile = ProfileSchema & ProfileSettingsOut;

export type ProfilePatchSchema = {
  telegramId: number;
} & Partial<Omit<Profile, "telegramId">>;

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

