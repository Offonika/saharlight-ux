import { setTelegramInitData } from '@/lib/telegram-auth';

export function useTelegramInitData(): string | null {
  try {
    const globalData = (window as any)?.Telegram?.WebApp?.initData;
    if (globalData) {
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

    return localStorage.getItem('tg_init_data');
  } catch {
    return null;
  }
}
