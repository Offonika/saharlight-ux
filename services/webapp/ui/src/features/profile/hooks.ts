import { useEffect, useState } from "react";
import { getProfile } from "./api";

export function useDefaultAfterMealMinutes(telegramId: number | null | undefined) {
  const [value, setValue] = useState<number | null>(null);

  useEffect(() => {
    if (!telegramId) return;
    getProfile(telegramId)
      .then((profile) => {
        const minutes =
          (profile as any).default_after_meal_minutes ??
          (profile as any).defaultAfterMealMinutes;
        if (typeof minutes === "number") {
          setValue(minutes);
        }
      })
      .catch((err) => {
        console.warn("Failed to load profile:", err);
      });
  }, [telegramId]);

  return value;
}

