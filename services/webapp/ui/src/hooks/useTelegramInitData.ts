import { useMemo } from "react";

export function useTelegramInitData() {
  return useMemo(() => localStorage.getItem("tg_init_data") || "", []);
}