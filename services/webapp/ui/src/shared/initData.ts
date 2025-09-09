export function hasInitData(): boolean {
  const initData =
    (window as unknown as { Telegram?: { WebApp?: { initData?: string } } })
      .Telegram?.WebApp?.initData;

  if (initData) {
    return true;
  }

  const urlData = new URLSearchParams(
    window.location.hash ? window.location.hash.substring(1) : '',
  ).get('tgWebAppData');

  return Boolean(urlData);
}
