import { request as baseRequest } from '@/lib/http';

const API_BASE = '/api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    return await baseRequest<T>(`${API_BASE}${path}`, init);
  } catch (error) {
    console.warn('[API] Backend request failed:', error);
    throw error;
  }
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

export type HttpClient = typeof http;
