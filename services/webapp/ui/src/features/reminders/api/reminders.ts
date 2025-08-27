import { Configuration } from "@sdk/runtime";
import { DefaultApi } from "@sdk/apis";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";

export function makeRemindersApi(initData: string) {
  const cfg = new Configuration({
    basePath: "",
    headers: { "X-Telegram-Init-Data": initData },
  });
  return new DefaultApi(cfg);
}

export function useRemindersApi() {
  const initData = useTelegramInitData();
  return makeRemindersApi(initData);
}

