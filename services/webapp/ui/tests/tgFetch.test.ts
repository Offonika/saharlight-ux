import { afterEach, describe, expect, it, vi } from 'vitest';

describe('tgFetch', () => {
  afterEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('defaults to /api when env is empty', async () => {
    vi.stubEnv('VITE_API_BASE', '');
    const mockFetch = vi.fn().mockResolvedValue(new Response(null));
    vi.stubGlobal('fetch', mockFetch);

    const { tgFetch } = await import('../src/api/tgFetch');
    await tgFetch('/foo');

    expect(mockFetch).toHaveBeenCalledWith('/api/foo', expect.any(Object));
  });

  it('uses VITE_API_BASE value', async () => {
    vi.stubEnv('VITE_API_BASE', '/custom');
    const mockFetch = vi.fn().mockResolvedValue(new Response(null));
    vi.stubGlobal('fetch', mockFetch);

    const { tgFetch } = await import('../src/api/tgFetch');
    await tgFetch('/bar');

    expect(mockFetch).toHaveBeenCalledWith('/custom/bar', expect.any(Object));
  });

  it('does not double prefix when path already includes base', async () => {
    vi.stubEnv('VITE_API_BASE', '/api');
    const mockFetch = vi.fn().mockResolvedValue(new Response(null));
    vi.stubGlobal('fetch', mockFetch);

    const { tgFetch } = await import('../src/api/tgFetch');
    await tgFetch('/api/baz');

    expect(mockFetch).toHaveBeenCalledWith('/api/baz', expect.any(Object));
  });
});
