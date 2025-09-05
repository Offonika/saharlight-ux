import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Save } from "lucide-react";
import { MedicalHeader } from "@/components/MedicalHeader";
import { useToast } from "@/hooks/use-toast";
import MedicalButton from "@/components/MedicalButton";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import Modal from "@/components/Modal";
import HelpHint from "@/components/HelpHint";
import ProfileHelpSheet from "@/components/ProfileHelpSheet";
import { useIsMobile } from "@/hooks/use-mobile";
import { useTranslation } from "@/i18n";
import { saveProfile, getProfile, patchProfile } from "@/features/profile/api";
import type { PatchProfileDto, RapidInsulin } from "@/features/profile/types";
import { getTimezones } from "@/api/timezones";
import { useTelegram } from "@/hooks/useTelegram";
import { useTelegramInitData } from "@/hooks/useTelegramInitData";
import { resolveTelegramId } from "./resolveTelegramId";
import { postOnboardingEvent } from "@/shared/api/onboarding";

type TherapyType = 'insulin' | 'tablets' | 'none' | 'mixed';

const rapidInsulinTypes: RapidInsulin[] = [
  'aspart',
  'lispro',
  'glulisine',
  'regular',
];

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
};

type ParsedProfile = {
  icr: number;
  cf: number;
  target: number;
  low: number;
  high: number;
  dia: number;
  preBolus: number;
  roundStep: number;
  carbUnits: 'g' | 'xe';
  gramsPerXe: number;
  rapidInsulinType: RapidInsulin;
  maxBolus: number;
  afterMealMinutes: number;
};

export const parseProfile = (
  profile: ProfileForm,
  therapyType?: TherapyType,
): ParsedProfile | null => {
  if (therapyType === 'tablets' || therapyType === 'none') {
    const gramsPerXe = Number(profile.gramsPerXe.replace(/,/g, '.'));
    const parsed = {
      icr: 0,
      cf: 0,
      target: Number(profile.target.replace(/,/g, '.')),
      low: Number(profile.low.replace(/,/g, '.')),
      high: Number(profile.high.replace(/,/g, '.')),
      dia: 0,
      preBolus: 0,
      roundStep: Number(profile.roundStep.replace(/,/g, '.')),
      carbUnits: profile.carbUnits,
      gramsPerXe: Number.isFinite(gramsPerXe) ? gramsPerXe : 0,
      rapidInsulinType: profile.rapidInsulinType,
      maxBolus: 0,
      afterMealMinutes: Number(profile.afterMealMinutes.replace(/,/g, '.')),
    } satisfies ParsedProfile;
    const validateGrams = parsed.carbUnits === 'xe';
    const numbersValid =
      [
        parsed.target,
        parsed.low,
        parsed.high,
        parsed.roundStep,
        parsed.afterMealMinutes,
        ...(validateGrams ? [parsed.gramsPerXe] : []),
      ].every((v) => Number.isFinite(v));
    const positiveValid =
      parsed.target > 0 &&
      parsed.low > 0 &&
      parsed.high > 0 &&
      parsed.roundStep > 0 &&
      parsed.afterMealMinutes >= 0 &&
      (!validateGrams || parsed.gramsPerXe > 0);
    const rangeValid =
      parsed.low < parsed.high &&
      parsed.low < parsed.target &&
      parsed.target < parsed.high &&
      parsed.afterMealMinutes <= 240 &&
      (parsed.carbUnits === 'g' || parsed.carbUnits === 'xe') &&
      (!validateGrams || parsed.gramsPerXe > 0);
    return numbersValid && positiveValid && rangeValid ? parsed : null;
  }

  const gramsPerXe = Number(profile.gramsPerXe.replace(/,/g, '.'));
  const parsed = {
    icr: Number(profile.icr.replace(/,/g, '.')),
    cf: Number(profile.cf.replace(/,/g, '.')),
    target: Number(profile.target.replace(/,/g, '.')),
    low: Number(profile.low.replace(/,/g, '.')),
    high: Number(profile.high.replace(/,/g, '.')),
    dia: Number(profile.dia.replace(/,/g, '.')),
    preBolus: Number(profile.preBolus.replace(/,/g, '.')),
    roundStep: Number(profile.roundStep.replace(/,/g, '.')),
    carbUnits: profile.carbUnits,
    gramsPerXe: Number.isFinite(gramsPerXe) ? gramsPerXe : 0,
    rapidInsulinType: profile.rapidInsulinType,
    maxBolus: Number(profile.maxBolus.replace(/,/g, '.')),
    afterMealMinutes: Number(profile.afterMealMinutes.replace(/,/g, '.')),
  } satisfies ParsedProfile;
  const validateGrams = parsed.carbUnits === 'xe';
  const numbersValid =
    [
      parsed.icr,
      parsed.cf,
      parsed.target,
      parsed.low,
      parsed.high,
      parsed.dia,
      parsed.preBolus,
      parsed.roundStep,
      parsed.maxBolus,
      parsed.afterMealMinutes,
      ...(validateGrams ? [parsed.gramsPerXe] : []),
    ].every((v) => Number.isFinite(v));
  const positiveValid =
    parsed.icr > 0 &&
    parsed.cf > 0 &&
    parsed.target > 0 &&
    parsed.low > 0 &&
    parsed.high > 0 &&
    parsed.dia >= 1 &&
    parsed.preBolus >= 0 &&
    parsed.roundStep > 0 &&
    parsed.maxBolus > 0 &&
    parsed.afterMealMinutes >= 0 &&
    (!validateGrams || parsed.gramsPerXe > 0);
  const rangeValid =
    parsed.low < parsed.high &&
    parsed.low < parsed.target &&
    parsed.target < parsed.high &&
    parsed.dia <= 24 &&
    parsed.preBolus <= 60 &&
    parsed.afterMealMinutes <= 240 &&
    (parsed.carbUnits === 'g' || parsed.carbUnits === 'xe') &&
    parsed.rapidInsulinType.length > 0 &&
    (!validateGrams || parsed.gramsPerXe > 0);
  return numbersValid && positiveValid && rangeValid ? parsed : null;
};

export const shouldWarnProfile = (
  profile: ParsedProfile,
  original?: ParsedProfile,
): boolean => {
  const icrCfWarn = profile.icr > 8 && profile.cf < 3;
  const diaWarn = profile.dia > 12;
  const carbUnitsWarn =
    !!original &&
    original.carbUnits !== profile.carbUnits &&
    original.icr === profile.icr &&
    profile.icr > 0;

  return icrCfWarn || diaWarn || carbUnitsWarn;
};

interface ProfileFormHeaderProps {
  onBack: () => void;
  therapyType?: TherapyType;
}

const ProfileFormHeader = ({
  onBack,
  therapyType,
}: ProfileFormHeaderProps) => {
  const isMobile = useIsMobile();
  const { t } = useTranslation();

  return (
    <>
      <MedicalHeader title={t('profile.title')} showBack onBack={onBack}>
        {!isMobile && <ProfileHelpSheet therapyType={therapyType} />}
      </MedicalHeader>
      {isMobile && (
        <div className="fixed bottom-4 right-4 z-50">
          <ProfileHelpSheet therapyType={therapyType} />
        </div>
      )}
    </>
  );
};

interface ProfileProps {
  therapyType?: TherapyType;
}

const Profile = ({ therapyType: therapyTypeProp }: ProfileProps) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const onboardingStep = searchParams.get("step") || undefined;
  const isOnboardingFlow = searchParams.get("flow") === "onboarding";
  const { toast } = useToast();
  const { user } = useTelegram();
  const initData = useTelegramInitData();
  const { t } = useTranslation();
  const deviceTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [profile, setProfile] = useState<ProfileForm>({
    icr: "",
    cf: "",
    target: "",
    low: "",
    high: "",
    timezone: deviceTz,
    timezoneAuto: true,
    dia: "",
    preBolus: "",
    roundStep: "",
    carbUnits: 'g',
    gramsPerXe: "",
    rapidInsulinType: 'aspart',
    maxBolus: "",
    afterMealMinutes: "",
  });
  const [original, setOriginal] = useState<ProfileForm | null>(null);
  const [timezones, setTimezones] = useState<string[]>([]);
  const [therapyType, setTherapyType] = useState<TherapyType>(
    therapyTypeProp ?? 'none',
  );
  const [originalTherapyType, setOriginalTherapyType] = useState<TherapyType>(
    therapyTypeProp ?? 'none',
  );

  const isInsulinTherapy =
    therapyType === 'insulin' || therapyType === 'mixed';

  const [warningOpen, setWarningOpen] = useState(false);
  const [pendingProfile, setPendingProfile] = useState<
    (
      ParsedProfile & {
        telegramId: number;
        patch: PatchProfileDto;
        therapyType?: TherapyType;
      }
    ) | null
  >(null);

  useEffect(() => {
    if (isOnboardingFlow) {
      postOnboardingEvent("onboarding_started", onboardingStep).catch(() =>
        undefined,
      );
    }
  }, [isOnboardingFlow, onboardingStep]);

  useEffect(() => {
    try {
      setTimezones(Intl.supportedValuesOf("timeZone"));
    } catch {
      getTimezones().then(setTimezones).catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    const telegramId = resolveTelegramId(user, initData);

    if (typeof telegramId !== "number") {
      return;
    }

    let cancelled = false;

    getProfile(telegramId)
      .then((data) => {
        if (cancelled) return;

        const icr =
          typeof data.icr === "number" && data.icr > 0
            ? data.icr.toString()
            : "";
        const cf =
          typeof data.cf === "number" && data.cf > 0
            ? data.cf.toString()
            : "";
        const target =
          typeof data.target === "number" && data.target > 0
            ? data.target.toString()
            : "";
        const low =
          typeof data.low === "number" && data.low > 0
            ? data.low.toString()
            : "";
        const high =
          typeof data.high === "number" && data.high > 0
            ? data.high.toString()
            : "";
        const dia =
          typeof data.dia === "number" && data.dia > 0
            ? data.dia.toString()
            : "";
        const preBolus =
          typeof data.preBolus === "number" && data.preBolus >= 0
            ? data.preBolus.toString()
            : "";
        const roundStep =
          typeof data.roundStep === "number" && data.roundStep > 0
            ? data.roundStep.toString()
            : "";
        const carbUnits = data.carbUnits === "xe" ? "xe" : "g";
        const gramsPerXe =
          typeof data.gramsPerXe === "number" && data.gramsPerXe > 0
            ? data.gramsPerXe.toString()
            : "";
        const rapidInsulinType: RapidInsulin =
          typeof data.rapidInsulinType === "string" &&
          rapidInsulinTypes.includes(
            data.rapidInsulinType as RapidInsulin,
          )
            ? (data.rapidInsulinType as RapidInsulin)
            : 'aspart';
        const maxBolus =
          typeof data.maxBolus === "number" && data.maxBolus > 0
            ? data.maxBolus.toString()
            : "";
        const afterMealMinutes =
          typeof data.afterMealMinutes === "number" &&
          data.afterMealMinutes >= 0
            ? data.afterMealMinutes.toString()
            : "";
        const timezone =
          typeof data.timezone === "string" && data.timezone
            ? data.timezone
            : deviceTz;
        const timezoneAuto = data.timezoneAuto === true;
        const therapyType = data.therapyType ?? 'none';

        const loaded: ProfileForm = {
          icr,
          cf,
          target,
          low,
          high,
          timezone,
          timezoneAuto,
          dia,
          preBolus,
          roundStep,
          carbUnits,
          gramsPerXe,
          rapidInsulinType,
          maxBolus,
          afterMealMinutes,
        };

        setProfile(loaded);
        setOriginal(loaded);
        setTherapyType(therapyType);
        setOriginalTherapyType(therapyType);

        if (timezoneAuto && timezone !== deviceTz) {
          patchProfile({
            timezone: deviceTz ?? null,
            timezoneAuto: true,
          })
            .then(() =>
              toast({
                title: t('profile.updated'),
                description: t('profile.timezoneUpdated'),
              }),
            )
            .catch((error) => {
              const message =
                error instanceof Error ? error.message : String(error);
              toast({
                title: t('profile.error'),
                description: message,
                variant: "destructive",
              });
            });
          setProfile((prev) => ({ ...prev, timezone: deviceTz }));
        }

      })
      .catch((error) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : String(error);
        toast({
          title: t('profile.error'),
          description: message,
          variant: "destructive",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [user, initData, toast]);

  const handleInputChange = (field: keyof ProfileForm, value: string) => {
    if (field === "timezone") {
      setProfile((prev) => ({ ...prev, timezone: value }));
      return;
    }
    if (field === "carbUnits") {
      setProfile((prev) => ({ ...prev, carbUnits: value as 'g' | 'xe' }));
      return;
    }
    if (field === "rapidInsulinType") {
      setProfile((prev) => ({
        ...prev,
        rapidInsulinType: value as RapidInsulin,
      }));
      return;
    }
    if (/^\d*(?:[.,]\d*)?$/.test(value)) {
      setProfile((prev) => ({ ...prev, [field]: value }));
    }
  };

  const buildPatch = (
    parsed: ParsedProfile,
    therapyTypeValue: TherapyType,
  ): PatchProfileDto => {
    if (!original) return {};
    const patch: PatchProfileDto = {};
    if (therapyTypeValue !== originalTherapyType)
      patch.therapyType = therapyTypeValue;
    if (profile.timezone !== original.timezone) patch.timezone = profile.timezone;
    if (profile.timezoneAuto !== original.timezoneAuto)
      patch.timezoneAuto = profile.timezoneAuto;
    if (profile.dia !== original.dia) patch.dia = parsed.dia;
    if (profile.preBolus !== original.preBolus) patch.preBolus = parsed.preBolus;
    if (profile.roundStep !== original.roundStep) patch.roundStep = parsed.roundStep;
    if (profile.carbUnits !== original.carbUnits) patch.carbUnits = parsed.carbUnits;
    if (profile.gramsPerXe !== original.gramsPerXe)
      patch.gramsPerXe = parsed.gramsPerXe;
    if (profile.rapidInsulinType !== original.rapidInsulinType)
      patch.rapidInsulinType = parsed.rapidInsulinType;
    if (profile.maxBolus !== original.maxBolus) patch.maxBolus = parsed.maxBolus;
    if (profile.afterMealMinutes !== original.afterMealMinutes)
      patch.afterMealMinutes = parsed.afterMealMinutes;
    return patch;
  };

  const saveParsedProfile = async (
    data: ParsedProfile & {
      telegramId: number;
      patch: PatchProfileDto;
      therapyType?: TherapyType;
    },
  ): Promise<void> => {
    try {
      if (Object.keys(data.patch).length > 0) {
        await patchProfile(data.patch);
      }

      const payload = {
        telegramId: data.telegramId,
        target: data.target,
        low: data.low,
        high: data.high,
      } as {
        telegramId: number;
        target: number;
        low: number;
        high: number;
        icr?: number;
        cf?: number;
      };

      if (data.therapyType !== 'tablets' && data.therapyType !== 'none') {
        payload.icr = data.icr;
        payload.cf = data.cf;
      }

      await saveProfile(payload);
      setOriginal(profile);
      if (data.therapyType) {
        setOriginalTherapyType(data.therapyType);
      }
      toast({
        title: t('profile.saved'),
        description: t('profile.settingsUpdated'),
      });
      postOnboardingEvent('profile_saved', onboardingStep, {
        timezone_set: Boolean(profile.timezone),
      }).catch(() => undefined);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      toast({
        title: t('profile.error'),
        description: message,
        variant: "destructive",
      });
    }
  };

  const handleSave = async () => {
    const telegramId = resolveTelegramId(user, initData);

    if (typeof telegramId !== "number") {
      toast({
        title: t('profile.error'),
        description: t('profile.invalidId'),
        variant: "destructive",
      });
      return;
    }

    const parsed = parseProfile(profile, therapyType);
    if (!parsed) {
      toast({
        title: t('profile.error'),
        description: t('profile.invalidValues'),
        variant: "destructive",
      });
      return;
    }

    const originalParsed = original
      ? parseProfile(original, therapyType) || undefined
      : undefined;

    if (shouldWarnProfile(parsed, originalParsed)) {
      setPendingProfile({
        telegramId,
        ...parsed,
        patch: buildPatch(parsed, therapyType),
        therapyType,
      });
      setWarningOpen(true);
      toast({
        title: t('profile.warning.title'),
        description: t('profile.warning.message'),
      });
      return;
    }

    await saveParsedProfile({
      telegramId,
      ...parsed,
      patch: buildPatch(parsed, therapyType),
      therapyType,
    });
  };

  const handleConfirmSave = async () => {
    if (!pendingProfile) return;
    await saveParsedProfile(pendingProfile);
    setPendingProfile(null);
    setWarningOpen(false);
  };

  return (
    <>
      <Modal
        open={warningOpen}
        onClose={() => setWarningOpen(false)}
        title={t('profile.warning.title')}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setWarningOpen(false)}>
              {t('profile.warning.cancel')}
            </Button>
            <MedicalButton onClick={handleConfirmSave}>
              {t('profile.warning.confirm')}
            </MedicalButton>
          </div>
        }
      >
        <p>{t('profile.warning.message')}</p>
      </Modal>

      <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
        <ProfileFormHeader
          onBack={() => navigate("/")}
          therapyType={therapyType}
        />

        <main className="container mx-auto px-4 py-6">
        <div className="medical-card animate-slide-up bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
        <div className="space-y-6">
          <div>
            <label
              htmlFor="therapyType"
              className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
            >
              {t('profileHelp.therapyType.title')}
              <HelpHint label="profileHelp.therapyType.title">
                {t('profileHelp.therapyType.definition')}
              </HelpHint>
            </label>
            <select
              id="therapyType"
              className="medical-input"
              value={therapyType}
              onChange={(e) => setTherapyType(e.target.value as TherapyType)}
            >
              <option value="insulin">
                {t('profileHelp.therapyType.options.insulin')}
              </option>
              <option value="tablets">
                {t('profileHelp.therapyType.options.tablets')}
              </option>
              <option value="none">
                {t('profileHelp.therapyType.options.none')}
              </option>
              <option value="mixed">
                {t('profileHelp.therapyType.options.mixed')}
              </option>
            </select>
          </div>

          {isInsulinTherapy && (
            <>
              {/* ICR */}
              <div>
                <label
                    htmlFor="icr"
                    className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                  >
                    {t('profileHelp.icr.title')}
                    <HelpHint label="profileHelp.icr.title">
                      {t('profileHelp.icr.definition')}
                    </HelpHint>
                  </label>
                  <div className="relative">
                    <input
                      id="icr"
                      type="text"
                      inputMode="decimal"
                      pattern="^\\d*(?:[.,]\\d*)?$"
                      value={profile.icr}
                      onChange={(e) => handleInputChange("icr", e.target.value)}
                      className="medical-input"
                      placeholder="12"
                    />
                    <span className="absolute right-3 top-3 text-muted-foreground text-sm">
                      {t('profileHelp.icr.unit')}
                    </span>
                  </div>
                </div>

                {/* Коэффициент коррекции */}
                <div>
                  <label
                    htmlFor="cf"
                    className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                  >
                    {t('profileHelp.cf.title')}
                    <HelpHint label="profileHelp.cf.title">
                      {t('profileHelp.cf.definition')}
                    </HelpHint>
                  </label>
                  <div className="relative">
                    <input
                      id="cf"
                      type="text"
                      inputMode="decimal"
                      pattern="^\\d*(?:[.,]\\д*)?$"
                      value={profile.cf}
                      onChange={(e) => handleInputChange("cf", e.target.value)}
                      className="medical-input"
                      placeholder="2.5"
                    />
                    <span className="absolute right-3 top-3 text-muted-foreground text-sm">
                      {t('profileHelp.cf.unit')}
                    </span>
                  </div>
                </div>
              </>
            )}

            {/* Целевой сахар */}
            <div>
              <label
                htmlFor="target"
                className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
              >
                {t('profileHelp.target.title')}
                <HelpHint label="profileHelp.target.title">
                  {t('profileHelp.target.definition')}
                </HelpHint>
              </label>
              <div className="relative">
                <input
                  id="target"
                  type="text"
                  inputMode="decimal"
                  pattern="^\\d*(?:[.,]\\d*)?$"
                  value={profile.target}
                  onChange={(e) => handleInputChange("target", e.target.value)}
                  className="medical-input"
                  placeholder="6.0"
                />
                <span className="absolute right-3 top-3 text-muted-foreground text-sm">
                  {t('profileHelp.target.unit')}
                </span>
              </div>
            </div>

            {/* Пороги */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="low"
                  className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                >
                  {t('profileHelp.low.title')}
                  <HelpHint label="profileHelp.low.title">
                    {t('profileHelp.low.definition')}
                  </HelpHint>
                </label>
                <div className="relative">
                  <input
                    id="low"
                    type="text"
                    inputMode="decimal"
                    pattern="^\\d*(?:[.,]\\d*)?$"
                    value={profile.low}
                    onChange={(e) => handleInputChange("low", e.target.value)}
                    className="medical-input"
                    placeholder="4.0"
                  />
                  <span className="absolute right-3 top-3 text-muted-foreground text-xs">
                    {t('profileHelp.low.unit')}
                  </span>
                </div>
              </div>

              <div>
                <label
                  htmlFor="high"
                  className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                >
                  {t('profileHelp.high.title')}
                  <HelpHint label="profileHelp.high.title">
                    {t('profileHelp.high.definition')}
                  </HelpHint>
                </label>
                <div className="relative">
                  <input
                    id="high"
                    type="text"
                    inputMode="decimal"
                    pattern="^\\d*(?:[.,]\\d*)?$"
                    value={profile.high}
                    onChange={(e) => handleInputChange("high", e.target.value)}
                    className="medical-input"
                    placeholder="10.0"
                  />
                  <span className="absolute right-3 top-3 text-muted-foreground text-xs">
                    {t('profileHelp.high.unit')}
                  </span>
                </div>
              </div>
            </div>

            {/* Расширенные настройки болюса */}
            <div className="space-y-6">
              <h3 className="font-semibold text-foreground">
                {t('profile.bolusSettings')}
              </h3>
              {isInsulinTherapy && (
                <>
                  {/* DIA */}
                  <div>
                    <label
                      htmlFor="dia"
                      className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                    >
                      {t('profileHelp.dia.title')}
                      <HelpHint label="profileHelp.dia.title">
                        {t('profileHelp.dia.definition')}
                      </HelpHint>
                    </label>
                    <input
                      id="dia"
                      type="text"
                      inputMode="decimal"
                      pattern="^\\d*(?:[.,]\\d*)?$"
                      value={profile.dia}
                      onChange={(e) => handleInputChange('dia', e.target.value)}
                      className="medical-input"
                      placeholder="4"
                    />
                  </div>
                  {/* Pre-bolus */}
                  <div>
                    <label
                      htmlFor="preBolus"
                      className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                    >
                      {t('profileHelp.preBolus.title')}
                      <HelpHint label="profileHelp.preBolus.title">
                        {t('profileHelp.preBolus.definition')}
                      </HelpHint>
                    </label>
                    <input
                      id="preBolus"
                      type="text"
                      inputMode="decimal"
                      pattern="^\\d*(?:[.,]\\d*)?$"
                      value={profile.preBolus}
                      onChange={(e) => handleInputChange('preBolus', e.target.value)}
                      className="medical-input"
                      placeholder="15"
                    />
                  </div>
                </>
              )}
              {/* Round step */}
              <div>
                <label
                  htmlFor="roundStep"
                  className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                >
                  {t('profileHelp.roundStep.title')}
                  <HelpHint label="profileHelp.roundStep.title">
                    {t('profileHelp.roundStep.definition')}
                  </HelpHint>
                </label>
                <input
                  id="roundStep"
                  type="text"
                  inputMode="decimal"
                  pattern="^\\d*(?:[.,]\\d*)?$"
                  value={profile.roundStep}
                  onChange={(e) => handleInputChange('roundStep', e.target.value)}
                  className="medical-input"
                  placeholder="0.5"
                />
              </div>
              {/* Carb unit and grams per XE */}
              <div>
                <label
                  htmlFor="carbUnits"
                  className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                >
                  {t('profileHelp.carbUnits.title')}
                  <HelpHint label="profileHelp.carbUnits.title">
                    {t('profileHelp.carbUnits.definition')}
                  </HelpHint>
                </label>
                <select
                  id="carbUnits"
                  className="medical-input"
                  value={profile.carbUnits}
                  onChange={(e) => handleInputChange('carbUnits', e.target.value)}
                >
                  <option value="g">{t('profileHelp.carbUnits.options.g')}</option>
                  <option value="xe">{t('profileHelp.carbUnits.options.xe')}</option>
                </select>
              </div>
              {profile.carbUnits === 'xe' && (
                <div>
                  <label
                    htmlFor="gramsPerXe"
                    className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                  >
                    {t('profileHelp.gramsPerXe.title')}
                    <HelpHint label="profileHelp.gramsPerXe.title">
                      {t('profileHelp.gramsPerXe.definition')}
                    </HelpHint>
                  </label>
                  <input
                    id="gramsPerXe"
                    type="text"
                    inputMode="decimal"
                    pattern="^\\d*(?:[.,]\\d*)?$"
                    value={profile.gramsPerXe}
                    onChange={(e) => handleInputChange('gramsPerXe', e.target.value)}
                    className="medical-input"
                    placeholder="12"
                  />
                </div>
              )}
              {isInsulinTherapy && (
                <>
                  {/* Rapid insulin type */}
                  <div>
                    <label
                      htmlFor="rapidInsulinType"
                      className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                    >
                      {t('profileHelp.rapidInsulinType.title')}
                      <HelpHint label="profileHelp.rapidInsulinType.title">
                        {t('profileHelp.rapidInsulinType.definition')}
                      </HelpHint>
                    </label>
                    <select
                      id="rapidInsulinType"
                      className="medical-input"
                      value={profile.rapidInsulinType}
                      onChange={(e) =>
                        handleInputChange(
                          'rapidInsulinType',
                          e.target.value as RapidInsulin,
                        )
                      }
                    >
                      {rapidInsulinTypes.map((type) => (
                        <option key={type} value={type}>
                          {t(`profileHelp.rapidInsulinType.options.${type}`)}
                        </option>
                      ))}
                    </select>
                  </div>
                  {/* Max bolus */}
                  <div>
                    <label
                      htmlFor="maxBolus"
                      className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                    >
                      {t('profileHelp.maxBolus.title')}
                      <HelpHint label="profileHelp.maxBolus.title">
                        {t('profileHelp.maxBolus.definition')}
                      </HelpHint>
                    </label>
                    <input
                      id="maxBolus"
                      type="text"
                      inputMode="decimal"
                      pattern="^\\d*(?:[.,]\\d*)?$"
                      value={profile.maxBolus}
                      onChange={(e) => handleInputChange('maxBolus', e.target.value)}
                      className="medical-input"
                      placeholder="10"
                    />
                  </div>
                </>
              )}
              {/* Default after-meal minutes */}
              <div>
                <label
                  htmlFor="afterMealMinutes"
                  className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                >
                  {t('profileHelp.afterMealMinutes.title')}
                  <HelpHint label="profileHelp.afterMealMinutes.title">
                    {t('profileHelp.afterMealMinutes.definition')}
                  </HelpHint>
                </label>
                <input
                  id="afterMealMinutes"
                  type="text"
                  inputMode="decimal"
                  pattern="^\\d*(?:[.,]\\д*)?$"
                  value={profile.afterMealMinutes}
                  onChange={(e) => handleInputChange('afterMealMinutes', e.target.value)}
                  className="medical-input"
                  placeholder="120"
                />
              </div>
            </div>

            {/* Таймзона */}
            <div>
              <label
                htmlFor="timezone"
                className="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
              >
                {t('profileHelp.timezone.title')}
                <HelpHint label="profileHelp.timezone.title">
                  {t('profileHelp.timezone.definition')}
                </HelpHint>
              </label>
              <input
                id="timezone"
                type="text"
                list="timezone-list"
                value={profile.timezone}
                onChange={(e) => handleInputChange("timezone", e.target.value)}
                className="medical-input"
                disabled={profile.timezoneAuto}
              />
              <datalist id="timezone-list">
                {timezones.map((tz) => {
                  let label = tz;
                  try {
                    const parts = new Intl.DateTimeFormat("en-US", {
                      timeZone: tz,
                      timeZoneName: "short",
                    })
                      .formatToParts(new Date())
                      .find((p) => p.type === "timeZoneName")?.value;
                    if (parts) {
                      const m = parts.match(/GMT([+-]\d{1,2})(?::(\d{2}))?/);
                      if (m) {
                        const sign = m[1].startsWith("-") ? "-" : "+";
                        const hours = Math.abs(parseInt(m[1], 10))
                          .toString()
                          .padStart(2, "0");
                        const minutes = m[2] ?? "00";
                        label = `UTC${sign}${hours}:${minutes} — ${tz}`;
                      }
                    }
                  } catch {
                    /* empty */
                  }
                  return <option key={tz} value={tz} label={label} />;
                })}
              </datalist>
              <div className="mt-2 flex items-center gap-2">
                <Checkbox
                  id="timezone-auto"
                  checked={profile.timezoneAuto}
                  onCheckedChange={(checked) => {
                    const auto = Boolean(checked);
                    setProfile((prev) => ({
                      ...prev,
                      timezoneAuto: auto,
                      timezone: auto ? deviceTz : prev.timezone,
                    }));
                  }}
                />
                <label htmlFor="timezone-auto" className="text-sm text-foreground">
                  {t('profileHelp.timezone.auto')}
                </label>
              </div>
            </div>

            {/* Кнопка сохранения */}
            <MedicalButton
              onClick={handleSave}
              className="w-full flex items-center justify-center gap-2"
              variant="medical"
              size="lg"
            >
              <Save className="w-4 h-4" />
              {t('profile.save')}
            </MedicalButton>
          </div>
        </div>

      </main>
    </div>
    </>
  );
};

export default Profile;
