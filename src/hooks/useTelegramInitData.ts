import { useMemo } from "react";

export function useTelegramInitData() {
  return useMemo(() => {
    const initData = (window as any)?.Telegram?.WebApp?.initData as string | undefined;
    if (initData && initData.length) return initData;
    return localStorage.getItem("tg_init_data") || "";
  }, []);
}