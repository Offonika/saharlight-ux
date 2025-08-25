import { useMemo } from "react";
import { Configuration } from "@sdk/runtime";
import { DefaultApi as RemindersApi } from "@sdk/apis";
import type { Reminder } from "@sdk";
import { useTelegramInitData } from "../../../hooks/useTelegramInitData";

export function useRemindersApi() {
  const initData = useTelegramInitData();
  const api = useMemo(() => {
    const cfg = new Configuration({
      basePath: "/api",
      headers: { "X-Telegram-Init-Data": initData },
    });
    return new RemindersApi(cfg);
  }, [initData]);

  const createReminder = (reminder: Reminder) =>
    api.remindersPost({ reminder });

  return { createReminder };
}

