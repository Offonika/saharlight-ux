const API_BASE = (
  import.meta.env.VITE_API_BASE as string | undefined
) ?? '/api';

function buildHeaders(init: RequestInit): Headers {
  const headers = new Headers(init.headers);

  if (
    init.body !== undefined &&
    !(init.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  const initData = (
    window as unknown as { Telegram?: { WebApp?: { initData?: string } } }
  )?.Telegram?.WebApp?.initData;

  if (initData && !headers.has('X-Telegram-Init-Data')) {
    headers.set('X-Telegram-Init-Data', initData);
  }

  return headers;
}

async function tgFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = buildHeaders(init);
  let body: BodyInit | null | undefined = init.body;

  if (body !== undefined && body !== null) {
    if (typeof body !== 'string' && !(body instanceof FormData)) {
      body = JSON.stringify(body);
    }
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, body });

  if (!res.ok) {
    let msg = '';
    try {
      msg = await res.text();
    } catch {
      // ignore
    }
    if (!msg) {
      msg = res.statusText || `Request failed with status ${res.status}`;
    }
    throw new Error(msg);
  }

  const isJson = res.headers.get('content-type')?.includes('application/json');
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

  return data as T;
}

export const api = {
  get: <T>(path: string) => tgFetch<T>(path),
  post: <T>(path: string, body: unknown) =>
    tgFetch<T>(path, { method: 'POST', body }),
  patch: <T>(path: string, body: unknown) =>
    tgFetch<T>(path, { method: 'PATCH', body }),
  put: <T>(path: string, body: unknown) =>
    tgFetch<T>(path, { method: 'PUT', body }),
  delete: <T>(path: string) => tgFetch<T>(path, { method: 'DELETE' }),
};

export { tgFetch };
