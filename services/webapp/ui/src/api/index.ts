import { httpClient, RequestOptions } from '@/lib/http';

export const api = {
  get: <T>(path: string, opts?: RequestOptions) =>
    httpClient.get<T>(path, { telegramAuth: true, ...opts }),
  post: <T>(path: string, body: unknown, opts?: RequestOptions) =>
    httpClient.post<T>(path, body, { telegramAuth: true, ...opts }),
  patch: <T>(path: string, body: unknown, opts?: RequestOptions) =>
    httpClient.patch<T>(path, body, { telegramAuth: true, ...opts }),
  put: <T>(path: string, body: unknown, opts?: RequestOptions) =>
    httpClient.put<T>(path, body, { telegramAuth: true, ...opts }),
  delete: <T>(path: string, opts?: RequestOptions) =>
    httpClient.delete<T>(path, { telegramAuth: true, ...opts }),
};

export type ApiClient = typeof api;
