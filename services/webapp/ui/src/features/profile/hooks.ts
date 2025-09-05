import { useEffect, useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { useTranslation } from "@/i18n";
import { getProfile } from "./api";

export function useDefaultAfterMealMinutes(
  telegramId: number | null | undefined,
) {
  const [value, setValue] = useState<number | null>(null);
  const { toast } = useToast();
  const { t } = useTranslation("profile");

  useEffect(() => {
    if (!telegramId) return;
    getProfile(telegramId)
      .then((profile) => {
        if (!profile) {
          toast({
            title: t("error"),
            description: t("notFound"),
            variant: "destructive",
          });
          return;
        }
        const minutes = profile.afterMealMinutes;
        if (typeof minutes === "number") {
          setValue(minutes);
        }
      })
      .catch((err) => {
        console.warn("Failed to load profile:", err);
      });
  }, [telegramId, toast, t]);

  return value;
}

