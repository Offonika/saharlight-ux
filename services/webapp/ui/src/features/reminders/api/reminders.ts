import { Configuration } from "@sdk/runtime.ts";
import { RemindersApi } from "@sdk/apis";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";

export function makeRemindersApi(initData: string) {
  const cfg = new Configuration({
    basePath: "",
    headers: { "X-Telegram-Init-Data": initData },
  });
  return new RemindersApi(cfg);
}

export function useRemindersApi() {
  const initData = useTelegramInitData();
  return makeRemindersApi(initData);
}
