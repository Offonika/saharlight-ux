import { tgFetch } from '../lib/tgFetch';

/**
 * A fetch wrapper that ensures Telegram init data headers and cookies are sent.
 */
export function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  return tgFetch(input, { ...init, credentials: 'include' });
}
