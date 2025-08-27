import { Configuration } from "../../../../libs/ts-sdk/runtime.ts";
import { DefaultApi } from "../../../../libs/ts-sdk/apis";

export async function getPlanLimit(userId: number, initData: string): Promise<number> {
  try {
    const cfg = new Configuration({
      basePath: "",
      headers: { "X-Telegram-Init-Data": initData }
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
