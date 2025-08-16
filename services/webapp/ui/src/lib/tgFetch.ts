export function tgFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const headers = new Headers(init.headers || {});
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.initData) {
    headers.set("X-Telegram-Init-Data", tg.initData);
  }
  return fetch(input, { credentials: "include", ...init, headers });
}
