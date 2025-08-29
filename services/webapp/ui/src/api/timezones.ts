export async function getTimezones(): Promise<string[]> {
  const res = await fetch('/api/timezones');
  if (!res.ok) {
    const errorText = await res.text().catch(() => '');
    const msg = errorText || 'Request failed';
    throw new Error(msg);
  }
  const data = await res.json();
  if (Array.isArray(data)) {
    return data as string[];
  }
  throw new Error('Invalid response');
}
