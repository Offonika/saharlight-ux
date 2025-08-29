import { getTelegramAuthHeaders } from '@/lib/telegram-auth';
import { mockApi } from './mock-server';

const API_BASE = '/api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);

  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const authHeaders = getTelegramAuthHeaders();
  Object.entries(authHeaders).forEach(([key, value]) => headers.set(key, value));

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
    });

    // Check if response is HTML (backend not available) - do this BEFORE parsing JSON
    const contentType = res.headers.get('content-type');
    if (contentType?.includes('text/html')) {
      throw new Error('Backend returned HTML instead of JSON');
    }

    const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    if (!res.ok) {
      const msg = typeof data.detail === 'string' ? data.detail : 'Request failed';
      throw new Error(msg);
    }
    return data as T;
  } catch (error) {
    console.warn('[API] Backend request failed, falling back to mock API:', error);
    // Fallback to mock API for development
    return await handleMockRequest<T>(path, init);
  }
}

async function handleMockRequest<T>(path: string, init: RequestInit): Promise<T> {
  const urlParams = new URLSearchParams(path.split('?')[1] || '');
  const telegramId = parseInt(urlParams.get('telegramId') || urlParams.get('telegram_id') || '12345');
  
  if (path.startsWith('/reminders')) {
    if (init.method === 'POST') {
      const body = JSON.parse(init.body as string);
      return await mockApi.createReminder(body.reminder || body) as T;
    } else {
      return await mockApi.getReminders(telegramId) as T;
    }
  }
  
  return {} as T;
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
