import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/telegram-auth', () => ({
  getTelegramAuthHeaders: () => ({}),
  setTelegramInitData: vi.fn(),
}));

const makeJsonResponse = () =>
  new Response('{}', {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

describe('http.request', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it('does not set Content-Type for FormData bodies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(makeJsonResponse());
    vi.stubGlobal('fetch', fetchMock);
    const { request } = await import('../src/api/http');
    const form = new FormData();
    form.append('field', 'value');
    await request('/upload', { method: 'POST', body: form });
    const init = fetchMock.mock.calls[0][1]!;
    const headers = init.headers as Headers;
    expect(headers.has('Content-Type')).toBe(false);
    expect(init.body).toBe(form);
  });
});

