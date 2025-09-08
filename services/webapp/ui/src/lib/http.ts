import { getTelegramAuthHeaders } from '@/lib/telegram-auth';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api';

export interface RequestOptions extends RequestInit {
  telegramAuth?: boolean;
}

export class HttpError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function buildHeaders(
  init: RequestInit,
  telegramAuth = false,
): Headers {
  const headers = new Headers(init.headers);

  if (
    init.body !== undefined &&
    !(init.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  if (telegramAuth) {
    const authHeaders = getTelegramAuthHeaders();
    Object.entries(authHeaders).forEach(([key, value]) =>
      headers.set(key, value),
    );
  }

  return headers;
}

export async function handleResponse<T>(res: Response): Promise<T> {
  const isJson = res.headers
    .get('content-type')
    ?.includes('application/json');

  let data: unknown;
  if (isJson) {
    try {
      data = await res.json();
    } catch {
      throw new Error('Некорректный ответ сервера');
    }
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const msg =
      typeof (data as Record<string, unknown> | undefined)?.detail === 'string'
        ? (data as Record<string, string>).detail
        : typeof data === 'string'
          ? data
          : 'Request failed';
    throw new HttpError(res.status, msg);
  }

  return data as T;
}

export async function httpRequest<T>(
  path: string,
  { telegramAuth = false, body, ...init }: RequestOptions = {},
): Promise<T> {
  let requestBody = body;
  if (requestBody !== undefined && requestBody !== null) {
    if (typeof requestBody !== 'string' && !(requestBody instanceof FormData)) {
      requestBody = JSON.stringify(requestBody);
    }
  }

  const headers = buildHeaders({ ...init, body: requestBody }, telegramAuth);
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    body: requestBody,
    headers,
  });
  return handleResponse<T>(res);
}

export const httpClient = {
  get: <T>(path: string, opts?: RequestOptions) => httpRequest<T>(path, opts),
  post: <T>(path: string, body: unknown, opts?: RequestOptions) =>
    httpRequest<T>(path, { ...opts, method: 'POST', body }),
  patch: <T>(path: string, body: unknown, opts?: RequestOptions) =>
    httpRequest<T>(path, { ...opts, method: 'PATCH', body }),
  put: <T>(path: string, body: unknown, opts?: RequestOptions) =>
    httpRequest<T>(path, { ...opts, method: 'PUT', body }),
  delete: <T>(path: string, opts?: RequestOptions) =>
    httpRequest<T>(path, { ...opts, method: 'DELETE' }),
};

export type HttpClient = typeof httpClient;
