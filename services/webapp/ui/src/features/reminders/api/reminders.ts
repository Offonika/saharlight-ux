import { Configuration } from "@sdk/runtime.ts";
import { RemindersApi } from "@sdk/apis";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";

export function makeRemindersApi(initData: string | null) {
  const headers: Record<string, string> = {};
  if (initData) {
    headers["X-Telegram-Init-Data"] = initData;
  }
  const cfg = new Configuration({
    basePath: "",
    headers,
  });
  return new RemindersApi(cfg);
}

export function useRemindersApi() {
  const initData = useTelegramInitData();
  return makeRemindersApi(initData);
}
