export function hasInitData(): boolean {
  const initData =
    (window as unknown as { Telegram?: { WebApp?: { initData?: string } } })
      .Telegram?.WebApp?.initData;

  if (initData) {
    return true;
  }

  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash;
  const urlData = new URLSearchParams(hash).get('tgWebAppData');

  return Boolean(urlData);
}
