import { Configuration } from "@sdk/runtime.ts";
import { RemindersApi } from "@sdk/apis";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";

export function makeRemindersApi(initData: string | null) {
  const cfg = new Configuration({
    basePath: "",
    headers: initData ? { "X-Telegram-Init-Data": initData } : undefined,
  });
  return new RemindersApi(cfg);
}

export function useRemindersApi() {
  const initData = useTelegramInitData();
  return makeRemindersApi(initData);
}
