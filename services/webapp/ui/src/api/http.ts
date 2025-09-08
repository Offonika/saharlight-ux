import { getTelegramAuthHeaders } from '@/lib/telegram-auth';

const API_BASE = '/api';

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T | null> {
  const headers = new Headers(init.headers);

  if (
    init.body !== undefined &&
    !(init.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  const authHeaders = getTelegramAuthHeaders();
  Object.entries(authHeaders).forEach(([key, value]) => headers.set(key, value));

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
    });

    // 204 has no body; skip JSON parsing
    if (res.status === 204) {
      return null;
    }

    // Validate content type before parsing
    const contentType = res.headers.get('content-type');
    if (contentType?.includes('text/html')) {
      throw new Error('Backend returned HTML instead of JSON');
    }
    if (!contentType?.includes('application/json')) {
      const type = contentType ?? 'unknown';
      throw new Error(`Unexpected content-type: ${type}`);
    }

    const data = (await res.json()) as Record<string, unknown>;
    if (!res.ok) {
      const msg = typeof data.detail === 'string' ? data.detail : 'Request failed';
      throw new Error(msg);
    }
    return data as T;
  } catch (error) {
    console.warn('[API] Backend request failed:', error);
    throw error;
  }
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

export type HttpClient = typeof http;
