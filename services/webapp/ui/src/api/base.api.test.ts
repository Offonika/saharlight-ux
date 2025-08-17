import { describe, it, expect, vi, afterEach } from 'vitest';

describe('API_BASE', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('is empty string when VITE_API_BASE is empty', async () => {
    vi.stubEnv('VITE_API_BASE', '');
    vi.resetModules();
    const { API_BASE } = await import('./base');
    expect(API_BASE).toBe('');
  });

  it('defaults to /api when VITE_API_BASE is undefined', async () => {
    const { API_BASE } = await import('./base');
    expect(API_BASE).toBe('/api');
  });
});

