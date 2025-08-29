export const resolveTelegramId = (
  user: { id?: number } | null,
  initData: string | null,
): number | undefined => {
  let telegramId = Number.isFinite(user?.id) ? user?.id : undefined;
  if (!telegramId) {
    let userStr: string | null = null;
    if (initData) {
      try {
        userStr = new URLSearchParams(initData).get("user");
      } catch (e) {
        console.error("[Profile] failed to parse initData:", e);
      }
    }
    if (userStr) {
      try {
        const parsed = JSON.parse(userStr);
        telegramId =
          typeof parsed.id === "number" && Number.isFinite(parsed.id)
            ? parsed.id
            : undefined;
      } catch (e) {
        console.error("[Profile] failed to parse initData user:", e);
      }
    } else {
      console.warn("[Profile] no user field in initData");
    }
  }
  return telegramId;
};
