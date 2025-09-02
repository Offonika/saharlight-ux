import { afterEach, describe, expect, it, vi } from 'vitest';

const makeJsonResponse = () =>
  new Response('{}', {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

describe('http request', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it('serializes JSON bodies and sets content type', async () => {
    const fetchMock = vi.fn().mockResolvedValue(makeJsonResponse());
    vi.stubGlobal('fetch', fetchMock);
    const { request } = await import('../src/lib/http');
    await request('/api/test', { method: 'POST', body: { a: 1 } });
    const init = fetchMock.mock.calls[0][1]!;
    expect(init.body).toBe('{"a":1}');
    const headers = init.headers as Headers;
    expect(headers.get('Content-Type')).toBe('application/json');
  });

  it('adds telegram headers when option enabled', async () => {
    const fetchMock = vi.fn().mockResolvedValue(makeJsonResponse());
    vi.stubGlobal('fetch', fetchMock);
    const auth = await import('../src/lib/telegram-auth');
    vi.spyOn(auth, 'getTelegramAuthHeaders').mockReturnValue({
      'x-telegram-init-data': 'init',
    });
    const { request } = await import('../src/lib/http');
    await request('/api/ping', {}, { telegram: true });
    const headers = fetchMock.mock.calls[0][1]!.headers as Headers;
    expect(headers.get('x-telegram-init-data')).toBe('init');
  });

  it('throws error on failed response', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: 'fail' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const { request } = await import('../src/lib/http');
    await expect(request('/api/boom')).rejects.toThrow('fail');
  });

  it('throws error on HTML response', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response('<html></html>', {
          status: 200,
          headers: { 'Content-Type': 'text/html' },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const { request } = await import('../src/lib/http');
    await expect(request('/api/boom')).rejects.toThrow(
      'Backend returned HTML instead of JSON',
    );
  });
});
