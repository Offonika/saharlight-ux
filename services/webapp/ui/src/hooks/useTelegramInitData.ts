import { useMemo } from "react";

export function useTelegramInitData(): string | null {
  return useMemo(() => {
    try {
      return globalThis.localStorage?.getItem("tg_init_data") ?? null;
    } catch {
      return null;
    }
  }, []);
}