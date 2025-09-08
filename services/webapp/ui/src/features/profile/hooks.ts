import { useEffect, useState } from "react";
import { getProfile } from "./api";

const DEFAULT_AFTER_MEAL_MINUTES = 120;

export function useDefaultAfterMealMinutes(
  telegramId: number | null | undefined,
) {
  const [value, setValue] = useState<number>(DEFAULT_AFTER_MEAL_MINUTES);

  useEffect(() => {
    if (!telegramId) return;
    let cancelled = false;
    getProfile()
      .then((profile) => {
        if (cancelled) return;
        const minutes = profile.afterMealMinutes;
        setValue(
          typeof minutes === "number"
            ? minutes
            : DEFAULT_AFTER_MEAL_MINUTES,
        );
      })
      .catch(() => {
        if (cancelled) return;
        setValue(DEFAULT_AFTER_MEAL_MINUTES);
      });
    return () => {
      cancelled = true;
    };
  }, [telegramId]);

  return value;
}

