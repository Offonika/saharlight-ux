import { useEffect, useState } from "react";
import { getProfile } from "./api";

export function useDefaultAfterMealMinutes(telegramId: number | null | undefined) {
  const [value, setValue] = useState<number | null>(null);

  useEffect(() => {
    if (!telegramId) return;
    getProfile(telegramId)
      .then((profile) => {
        if (!profile) return;
        const minutes = profile.afterMealMinutes;
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

