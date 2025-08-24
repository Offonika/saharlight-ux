import { getTelegramAuthHeaders } from '@/lib/telegram-auth';

const API_BASE = '/api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);

  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const authHeaders = getTelegramAuthHeaders();
  Object.entries(authHeaders).forEach(([key, value]) => headers.set(key, value));

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) {
    const msg = typeof data.detail === 'string' ? data.detail : 'Request failed';
    throw new Error(msg);
  }
  return data as T;
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

export type HttpClient = typeof http;
