import { useMemo } from "react";

interface TelegramWebAppWindow extends Window {
  Telegram?: { WebApp?: { initData?: string } };
}

export function useTelegramInitData() {
  return useMemo(() => {
    const w = typeof window !== "undefined" ? (window as TelegramWebAppWindow) : undefined;
    if (w?.Telegram?.WebApp?.initData) return w.Telegram.WebApp.initData;

    // DEV: читаем из localStorage (записывается вручную в консоли)
    return (typeof window !== "undefined" ? localStorage.getItem("tg_init_data") : "") || "";
  }, []);
}
