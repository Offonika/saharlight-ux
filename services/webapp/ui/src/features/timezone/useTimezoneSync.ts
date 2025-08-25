import { useEffect, useRef } from "react";
import { useTelegramInitData } from "../../hooks/useTelegramInitData";
import { getBrowserTimeZone } from "../../shared/timezone";

function getTelegramUserId(initData: string): number {
  try {
    const raw = new URLSearchParams(initData).get("user");
    if (!raw) return 0;
    const u = JSON.parse(decodeURIComponent(raw));
    return Number(u?.id ?? 0);
  } catch { return 0; }
}

export function useTimezoneSync() {
  const ran = useRef(false);
  const initData = useTelegramInitData();

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const telegramId = getTelegramUserId(initData);
    if (!telegramId) return;

    (async () => {
      const tz = getBrowserTimeZone();
      try {
        // что хранится на сервере?
        const response = await fetch("/api/timezone", {
          headers: {
            "X-Telegram-Init-Data": initData,
          },
        });
        
        let serverTz = "UTC";
        if (response.ok) {
          const current = await response.json();
          serverTz = (current?.tz || current?.TZ || current?.timezone || "UTC").toString();
        }

        if (serverTz !== tz) {
          const putResponse = await fetch("/api/timezone", {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              "X-Telegram-Init-Data": initData,
            },
            body: JSON.stringify({ tz }),
          });
          
          if (putResponse.ok) {
            console.log(`[TZ] updated on server: ${serverTz} → ${tz}`);
          } else {
            console.warn(`[TZ] failed to update timezone:`, putResponse.status);
          }
        } else {
          console.log(`[TZ] up-to-date: ${tz}`);
        }
      } catch (e) {
        // Не блокируем UI, просто лог
        console.warn("[TZ] sync skipped:", e);
      }
    })();
  }, [initData]);
}