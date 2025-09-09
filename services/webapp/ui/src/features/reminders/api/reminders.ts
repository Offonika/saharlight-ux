import { useEffect, useMemo } from "react";
import { Configuration } from "@sdk/runtime.ts";
import { RemindersApi } from "@sdk/apis";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";
import { setTelegramInitData } from "@/lib/telegram-auth";
import { buildHeaders } from "@/api/http";

export function makeRemindersApi() {
  const hdrs = buildHeaders({ headers: {} }, true);
  const cfg = new Configuration({
    basePath: "/api",
    headers: Object.fromEntries(hdrs.entries()),
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
