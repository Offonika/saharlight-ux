const HEADER = 'Authorization';
const LS_KEY = 'tg_init_data';

export function getDevInitData(): string | null {
  if (typeof localStorage !== 'undefined') {
    const ls = localStorage.getItem(LS_KEY);
    if (ls) return ls;
  }
  const envData = (import.meta.env as Record<string, string | undefined>)
    .VITE_TELEGRAM_INIT_DATA;
  return envData ?? null;
}

let storedInitData: string | null = null;

export function setTelegramInitData(data: string): void {
  storedInitData = data;
  try {
    localStorage.setItem(LS_KEY, data);
  } catch {
    /* ignore */
  }
}

function getStoredInitData(): string | null {
  if (storedInitData) return storedInitData;
  try {
    const ls = localStorage.getItem(LS_KEY);
    if (ls) {
      storedInitData = ls;
      return ls;
    }
  } catch {
    /* ignore */
  }
  if (import.meta.env.DEV) {
    return getDevInitData();
  }
  return null;
}

export function isInitDataFresh(initData: string): boolean {
  try {
    const authDateStr = new URLSearchParams(initData).get('auth_date');
    if (!authDateStr) return false;
    const authDate = Number(authDateStr);
    if (!Number.isFinite(authDate)) return false;
    const now = Math.floor(Date.now() / 1000);
    if (authDate > now + 60) return false;
    if (now - authDate > 60 * 60 * 24) return false;
    return true;
  } catch {
    return false;
  }
}

export function getTelegramAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const initData = getStoredInitData();
  if (initData) {
    if (isInitDataFresh(initData)) {
      headers[HEADER] = `tg ${initData}`;
    } else {
      storedInitData = null;
      try {
        localStorage.removeItem(LS_KEY);
      } catch {
        /* ignore */
      }
    }
  }
  return headers;
}

export { LS_KEY as TELEGRAM_INIT_DATA_KEY };
