import { afterEach, describe, expect, it, vi } from 'vitest';

const makeJsonResponse = () =>
  new Response('{}', {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

describe('tgFetch', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('prefixes base url and adds telegram header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(makeJsonResponse());
    vi.stubGlobal('fetch', fetchMock);
    (window as unknown as { Telegram: { WebApp: { initData: string } } }).Telegram = {
      WebApp: { initData: 'init' },
    };

    const { tgFetch } = await import('../src/lib/tgFetch');
    await tgFetch('/ping');

    expect(fetchMock).toHaveBeenCalledWith('/api/ping', expect.any(Object));
    const headers = fetchMock.mock.calls[0][1]!.headers as Headers;
    expect(headers.get('X-Telegram-Init-Data')).toBe('init');
  });

  it('overrides base url via env', async () => {
    vi.stubEnv('VITE_API_BASE', 'http://example.com');
    const fetchMock = vi.fn().mockResolvedValue(makeJsonResponse());
    vi.stubGlobal('fetch', fetchMock);
    const { tgFetch } = await import('../src/lib/tgFetch');
    await tgFetch('/test');
    expect(fetchMock).toHaveBeenCalledWith('http://example.com/test', expect.any(Object));
  });

  it('serializes JSON bodies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(makeJsonResponse());
    vi.stubGlobal('fetch', fetchMock);
    const { api } = await import('../src/lib/tgFetch');
    await api.post('/item', { a: 1 });
    const init = fetchMock.mock.calls[0][1]!;
    expect(init.method).toBe('POST');
    expect(init.body).toBe('{"a":1}');
    const headers = init.headers as Headers;
    expect(headers.get('Content-Type')).toBe('application/json');
  });

  it('does not set Content-Type for FormData bodies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(makeJsonResponse());
    vi.stubGlobal('fetch', fetchMock);
    const { tgFetch } = await import('../src/lib/tgFetch');
    const form = new FormData();
    form.append('field', 'value');
    await tgFetch('/upload', { method: 'POST', body: form });
    const init = fetchMock.mock.calls[0][1]!;
    const headers = init.headers as Headers;
    expect(headers.has('Content-Type')).toBe(false);
    expect(init.body).toBe(form);
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
    const { tgFetch } = await import('../src/lib/tgFetch');
    await expect(tgFetch('/boom')).rejects.toThrow('fail');
  });

  it('api.delete uses DELETE method', async () => {
    const fetchMock = vi.fn().mockResolvedValue(makeJsonResponse());
    vi.stubGlobal('fetch', fetchMock);
    const { api } = await import('../src/lib/tgFetch');
    await api.delete('/item/1');
    const init = fetchMock.mock.calls[0][1]!;
    expect(init.method).toBe('DELETE');
  });
});
