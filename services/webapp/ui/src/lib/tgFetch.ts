import { request } from './http';

const API_BASE = (
  import.meta.env.VITE_API_BASE as string | undefined
) ?? '/api';

function tgFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(`${API_BASE}${path}`, init, { telegram: true });
}

export const api = {
  get: <T>(path: string) => tgFetch<T>(path),
  post: <T>(path: string, body: unknown) => tgFetch<T>(path, { method: 'POST', body }),
  patch: <T>(path: string, body: unknown) => tgFetch<T>(path, { method: 'PATCH', body }),
  put: <T>(path: string, body: unknown) => tgFetch<T>(path, { method: 'PUT', body }),
  delete: <T>(path: string) => tgFetch<T>(path, { method: 'DELETE' }),
};

export { tgFetch };
