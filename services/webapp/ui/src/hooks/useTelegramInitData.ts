import {
  setTelegramInitData,
  TELEGRAM_INIT_DATA_KEY,
  isInitDataFresh,
} from '@/lib/telegram-auth';

export function useTelegramInitData(): string | null {
  try {
    const globalData = (window as any)?.Telegram?.WebApp?.initData;
    if (globalData) {
      setTelegramInitData(globalData);
      return globalData;
    }

    let tgWebAppData: string | null = null;

    try {
      const hash = window.location.hash.startsWith('#')
        ? window.location.hash.slice(1)
        : window.location.hash;
      tgWebAppData = new URLSearchParams(hash).get('tgWebAppData');
    } catch {
      tgWebAppData = null;
    }

    if (tgWebAppData) {
      setTelegramInitData(tgWebAppData);
      return tgWebAppData;
    }

    try {
      const saved = localStorage.getItem(TELEGRAM_INIT_DATA_KEY);
      if (saved) {
        if (isInitDataFresh(saved)) {
          setTelegramInitData(saved);
          return saved;
        }
        localStorage.removeItem(TELEGRAM_INIT_DATA_KEY);
      }
    } catch {
      /* ignore */
    }

    return null;
  } catch {
    return null;
  }
}
