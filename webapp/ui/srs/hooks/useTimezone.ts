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
      // @ts-ignore
      if (window?.Telegram?.WebApp?.sendData) {
        // @ts-ignore
        window.Telegram.WebApp.sendData(value);
      }
      await fetch("/api/timezone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tz: value }),
      });
    } catch (e) { console.warn("submit timezone failed", e); }
  }, [tz, detect]);

  return { tz, setTz, detect, submit };
}
