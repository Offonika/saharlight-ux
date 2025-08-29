import { getTelegramAuthHeaders } from '@/lib/telegram-auth';

const rawBase =
  ((import.meta.env.VITE_API_BASE as string | undefined) || '/api').replace(/\/$/, '');
export const API_BASE = rawBase || '/api';

export const tgFetch: typeof fetch = (input: RequestInfo | URL, init: RequestInit = {}) => {
  let url: RequestInfo | URL = input;
  if (typeof input === 'string') {
    const isAbsolute = /^https?:\/\//.test(input);
    if (!isAbsolute) {
      if (input.startsWith(API_BASE)) {
        url = input;
      } else if (input.startsWith('/')) {
        url = `${API_BASE}${input}`;
      } else {
        url = `${API_BASE}/${input}`;
      }
    }
  }

  const headers = new Headers(init.headers);
  Object.entries(getTelegramAuthHeaders()).forEach(([key, value]) =>
    headers.set(key, value),
  );

  return fetch(url, { ...init, headers });
};
