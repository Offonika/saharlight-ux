import { useEffect, useMemo } from "react";
import { Configuration } from "@sdk/runtime.ts";
import { RemindersApi } from "@sdk/apis";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";
import { getTelegramAuthHeaders, setTelegramInitData } from "@/lib/telegram-auth";

export function makeRemindersApi() {
  const cfg = new Configuration({
    basePath: "/api",
    headers: getTelegramAuthHeaders(),
  });
  return new RemindersApi(cfg);
}

export function useRemindersApi() {
  const initData = useTelegramInitData();
  useEffect(() => {
    if (initData) {
      setTelegramInitData(initData);
    }
  }, [initData]);
  return useMemo(() => makeRemindersApi(), [initData]);
}
