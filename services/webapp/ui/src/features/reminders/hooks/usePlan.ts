import { Configuration } from '@sdk/runtime.ts';
import { DefaultApi } from "@sdk/apis";

export async function getPlanLimit(userId: number, initData: string | null): Promise<number> {
  try {
    const cfg = new Configuration({
      basePath: "",
      headers: initData ? { "X-Telegram-Init-Data": initData } : undefined,
    });
    const api = new DefaultApi(cfg);
    const res = await api.remindersGetRaw({ telegramId: userId });
    const limitHeader =
      res.raw.headers.get("X-Plan-Limit") ?? res.raw.headers.get("x-plan-limit");
    if (limitHeader) {
      const limit = parseInt(limitHeader, 10);
      if (!isNaN(limit)) {
        return limit;
      }
    }
    return 5;
  } catch (error) {
    console.warn("Failed to get plan limit, defaulting to free tier:", error);
    return 5;
  }
}
