import { Configuration, RemindersApi } from "../../../../libs/ts-sdk";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";

export function makeRemindersApi(initData: string) {
  const cfg = new Configuration({
    basePath: "/api",
    headers: { "X-Telegram-Init-Data": initData },
  });
  return new RemindersApi(cfg as any);
}

export function useRemindersApi() {
  const initData = useTelegramInitData();
  return makeRemindersApi(initData);
}