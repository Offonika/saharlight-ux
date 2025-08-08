// webapp/ui/src/hooks/useTimezone.ts
import { useEffect, useState, useCallback } from "react";

export function useTimezone() {
  const [tz, setTz] = useState<string>("");

  const detect = useCallback(() => {
    const val = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
    setTz(val);
    return val;
  }, []);

  useEffect(() => { detect(); }, [detect]);

  const submit = useCallback(async (forceDetect = false) => {
    const value = forceDetect ? detect() : tz;
    if (!value) return;
    try {
      if (window?.Telegram?.WebApp?.sendData) {
        window.Telegram.WebApp.sendData(value);
      }
      const send = async () =>
        fetch("/api/timezone", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tz: value }),
        });
      let response = await send();
      if (!response.ok) {
        console.error("submit timezone failed", response.statusText);
        response = await send();
        if (!response.ok) {
          console.error("submit timezone retry failed", response.statusText);
          window.Telegram?.WebApp?.showAlert?.(
            "Не удалось сохранить часовой пояс. Попробуйте позже."
          );
        }
      }
    } catch (e) {
      console.warn("submit timezone failed", e);
      window.Telegram?.WebApp?.showAlert?.(
        "Не удалось сохранить часовой пояс. Попробуйте позже."
      );
    }
  }, [tz, detect]);

  return { tz, setTz, detect, submit };
}
