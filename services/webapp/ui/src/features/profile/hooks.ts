import { useEffect, useState } from "react";
import { getProfile } from "./api";
import type { Profile } from "./types";
import { useToast } from "@/hooks/use-toast";
import { useTranslation } from "@/i18n";

export function useDefaultAfterMealMinutes(
  telegramId: number | null | undefined,
) {
  const [value, setValue] = useState<number | null>(null);
  const { toast } = useToast();
  const { t } = useTranslation();

  useEffect(() => {
    if (!telegramId) return;
    getProfile(telegramId)
      .then((profile: Profile) => {
        const minutes = profile.afterMealMinutes;
        if (typeof minutes === "number") {
          setValue(minutes);
        }
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : String(err);
        if (/not found/i.test(message) || message.includes("не найден")) {
          toast({ title: t('profile.notFound'), variant: "destructive" });
        } else {
          console.warn('Failed to load profile:', err);
        }
      });
  }, [telegramId, toast, t]);

  return value;
}

