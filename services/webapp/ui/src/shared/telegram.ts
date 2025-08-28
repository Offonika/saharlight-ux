export function getTelegramUserId(initData: string | null): number {
  // initData = 'query_id=...&user=%7B...%7D&...'
  if (!initData) return 0;
  try {
    const params = new URLSearchParams(initData);
    const raw = params.get("user");
    if (!raw) return 0;
    const user = JSON.parse(decodeURIComponent(raw));
    return Number(user?.id ?? 0);
  } catch {
    return 0;
  }
}