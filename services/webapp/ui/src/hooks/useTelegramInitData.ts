const AUTH_DATE_MAX_AGE = 24 * 60 * 60; // 24 hours in seconds

export function useTelegramInitData(): string | null {
  try {
    const globalData = (window as any)?.Telegram?.WebApp?.initData;
    if (globalData) {
      try {
        localStorage.setItem("tg_init_data", globalData);
      } catch {
        /* ignore */
      }
      return globalData;
    }

    const stored = localStorage.getItem("tg_init_data");
    if (!stored) {
      return null;
    }

    const params = new URLSearchParams(stored);
    const authDateStr = params.get("auth_date");
    if (authDateStr) {
      const authDate = Number(authDateStr);
      if (!Number.isFinite(authDate) || Date.now() / 1000 - authDate > AUTH_DATE_MAX_AGE) {
        try {
          localStorage.removeItem("tg_init_data");
        } catch {
          /* ignore */
        }
        return null;
      }
    }

    return stored;
  } catch {
    return null;
  }
}
