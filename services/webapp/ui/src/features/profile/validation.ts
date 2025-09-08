import type { RapidInsulin, TherapyType } from './types';

type ProfileForm = {
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
  carbUnits: 'g' | 'xe';
  gramsPerXe: string;
  rapidInsulinType: RapidInsulin;
  maxBolus: string;
  afterMealMinutes: string;
  quietStart: string;
  quietEnd: string;
  sosContact: string | null;
  sosAlertsEnabled: boolean;
};

type ParsedProfile = {
  icr?: number;
  cf?: number;
  target?: number;
  low?: number;
  high?: number;
  dia?: number;
  preBolus?: number;
  roundStep?: number;
  carbUnits: 'g' | 'xe';
  gramsPerXe?: number;
  rapidInsulinType?: RapidInsulin;
  maxBolus?: number;
  afterMealMinutes?: number;
};

type FieldErrors = Partial<Record<keyof ProfileForm, string>>;

export const parseProfile = (
  profile: ProfileForm,
  therapyType?: TherapyType,
): { data: ParsedProfile; errors: FieldErrors } => {
  const errors: FieldErrors = {};
  const isNonInsulin = therapyType === 'tablets' || therapyType === 'none';

  const parseNumber = (
    field: keyof ProfileForm,
    value: string,
    {
      required = true,
      min,
      max,
      allowZero = false,
    }: {
      required?: boolean;
      min?: number;
      max?: number;
      allowZero?: boolean;
    } = {},
  ): number | undefined => {
    if (value.trim() === '') {
      if (required) errors[field] = 'required';
      return undefined;
    }
    const num = Number(value.replace(/,/g, '.'));
    if (!Number.isFinite(num)) {
      errors[field] = 'invalid';
      return undefined;
    }
    if (
      (!allowZero && num <= 0) ||
      (allowZero && num < 0) ||
      (min !== undefined && num < min) ||
      (max !== undefined && num > max)
    ) {
      errors[field] = 'out_of_range';
    }
    return num;
  };

  const icr = isNonInsulin ? 0 : parseNumber('icr', profile.icr);
  const cf = isNonInsulin ? 0 : parseNumber('cf', profile.cf);
  const target = parseNumber('target', profile.target);
  const low = parseNumber('low', profile.low);
  const high = parseNumber('high', profile.high);
  const dia = isNonInsulin
    ? 0
    : parseNumber('dia', profile.dia, { min: 1, max: 24 });
  const preBolus = isNonInsulin
    ? 0
    : parseNumber('preBolus', profile.preBolus, {
        allowZero: true,
        max: 60,
      });
  const roundStep = parseNumber('roundStep', profile.roundStep);

  const carbUnits = profile.carbUnits;
  if (carbUnits !== 'g' && carbUnits !== 'xe') {
    errors.carbUnits = 'invalid';
  }

  const gramsPerXe = parseNumber('gramsPerXe', profile.gramsPerXe, {
    required: carbUnits === 'xe',
  });

  const rapidInsulinType = profile.rapidInsulinType;
  if (!isNonInsulin && !rapidInsulinType) {
    errors.rapidInsulinType = 'required';
  }

  const maxBolus = isNonInsulin ? 0 : parseNumber('maxBolus', profile.maxBolus);
  const afterMealMinutes = parseNumber(
    'afterMealMinutes',
    profile.afterMealMinutes,
    { allowZero: true, max: 240 },
  );

  if (
    profile.sosContact !== null &&
    profile.sosContact !== '' &&
    !/^\d+$/.test(profile.sosContact)
  ) {
    errors.sosContact = 'invalid';
  }

  if (
    low !== undefined &&
    high !== undefined &&
    target !== undefined &&
    (low >= high || low >= target || target >= high)
  ) {
    if (!errors.low) errors.low = 'out_of_range';
    if (!errors.high) errors.high = 'out_of_range';
    if (!errors.target) errors.target = 'out_of_range';
  }

  return {
    data: {
      icr,
      cf,
      target,
      low,
      high,
      dia,
      preBolus,
      roundStep,
      carbUnits,
      gramsPerXe,
      rapidInsulinType,
      maxBolus,
      afterMealMinutes,
    },
    errors,
  };
};

export const shouldWarnProfile = (
  profile: ParsedProfile,
  original?: ParsedProfile,
): boolean => {
  const icrCfWarn =
    profile.icr !== undefined &&
    profile.cf !== undefined &&
    profile.icr > 8 &&
    profile.cf < 3;
  const diaWarn = profile.dia !== undefined && profile.dia > 12;
  const carbUnitsWarn =
    !!original &&
    original.carbUnits !== profile.carbUnits &&
    original.icr === profile.icr &&
    profile.icr !== undefined &&
    profile.icr > 0;

  return icrCfWarn || diaWarn || carbUnitsWarn;
};

export type { ProfileForm, ParsedProfile, FieldErrors };
