interface TelegramWebApp {
  initData?: string;
}

interface TelegramWindow extends Window {
  Telegram?: { WebApp?: TelegramWebApp };
}

export async function tgFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const initData = typeof window !== 'undefined'
    ? (window as TelegramWindow).Telegram?.WebApp?.initData
    : undefined;
  const headers = new Headers(init.headers ?? {});
  if (initData) {
    headers.set("X-Telegram-Init-Data", initData);
  }
  return fetch(input, { ...init, headers });
}
