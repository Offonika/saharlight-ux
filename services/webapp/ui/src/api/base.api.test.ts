import { describe, it, expect, vi, afterEach } from 'vitest';

describe('API_BASE', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('defaults to /api when VITE_API_URL is empty', async () => {
    vi.stubEnv('VITE_API_URL', '');
    vi.resetModules();
    const { API_BASE } = await import('./base');
    expect(API_BASE).toBe('/api');
  });

  it('defaults to /api when VITE_API_URL is undefined', async () => {
    const { API_BASE } = await import('./base');
    expect(API_BASE).toBe('/api');
  });
});

