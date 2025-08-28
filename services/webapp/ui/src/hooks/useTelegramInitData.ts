export function useTelegramInitData(): string | null {
  try {
    return localStorage.getItem("tg_init_data");
  } catch {
    return null;
  }
}
