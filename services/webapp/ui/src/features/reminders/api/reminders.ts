import { Configuration } from "@sdk/runtime";
import { DefaultApi as RemindersApi } from "@sdk/apis";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";

export function makeRemindersApi(initData: string) {
  const cfg = new Configuration({
    basePath: "/api",
    headers: { "X-Telegram-Init-Data": initData },
  });
  return new RemindersApi(cfg);
}

// Пример: в компоненте
export function useRemindersApi() {
  const initData = useTelegramInitData();
  return makeRemindersApi(initData);
}
