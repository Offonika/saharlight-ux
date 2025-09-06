export function useTelegramInitData(): string | null {
  try {
    const globalData = (window as any)?.Telegram?.WebApp?.initData;
    return globalData || localStorage.getItem("tg_init_data");
  } catch {
    return null;
  }
}
