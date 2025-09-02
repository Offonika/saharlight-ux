import { getTelegramAuthHeaders } from './telegram-auth';

interface BuildHeadersOptions {
  telegram?: boolean;
}

export function buildHeaders(
  init: RequestInit,
  { telegram = false }: BuildHeadersOptions = {},
): Headers {
  const headers = new Headers(init.headers);

  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (telegram) {
    const tgHeaders = getTelegramAuthHeaders();
    Object.entries(tgHeaders).forEach(([key, value]) => {
      if (!headers.has(key)) {
        headers.set(key, value);
      }
    });
  }

  return headers;
}

export async function handleResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get('content-type');
  if (contentType?.includes('text/html')) {
    throw new Error('Backend returned HTML instead of JSON');
  }

  const isJson = contentType?.includes('application/json');
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
    throw new Error(msg);
  }

  return data as T;
}

interface RequestOptions {
  telegram?: boolean;
}

export async function request<T>(
  url: string,
  init: RequestInit = {},
  opts: RequestOptions = {},
): Promise<T> {
  let body: BodyInit | null | undefined = init.body;

  if (body !== undefined && body !== null) {
    if (typeof body !== 'string' && !(body instanceof FormData)) {
      body = JSON.stringify(body);
    }
  }

  const headers = buildHeaders({ ...init, body }, opts);
  const res = await fetch(url, { ...init, headers, body });
  return handleResponse<T>(res);
}
