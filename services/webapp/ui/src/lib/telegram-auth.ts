const HEADER = 'Authorization';
const LS_KEY = 'tg_init_data';

export function getDevInitData(): string | null {
  if (typeof localStorage !== 'undefined') {
    const ls = localStorage.getItem(LS_KEY);
    if (ls) return ls;
  }
  const envData = (import.meta.env as Record<string, string | undefined>).VITE_TELEGRAM_INIT_DATA;
  return envData ?? null;
}

export function getTelegramAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const globalInitData = (
    window as unknown as { Telegram?: { WebApp?: { initData?: string } } }
  )?.Telegram?.WebApp?.initData;
  const initData =
    globalInitData || (import.meta.env.DEV ? getDevInitData() : null);
  if (initData) {
    headers[HEADER] = `tg ${initData}`;
  }
  return headers;
}

export { LS_KEY as TELEGRAM_INIT_DATA_KEY };
