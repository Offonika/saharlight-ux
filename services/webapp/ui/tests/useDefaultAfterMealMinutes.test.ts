import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/features/profile/api', () => ({
  getProfile: vi.fn(),
}));

import { useDefaultAfterMealMinutes } from '../src/features/profile/hooks';
import { getProfile } from '../src/features/profile/api';

describe('useDefaultAfterMealMinutes', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('uses afterMealMinutes when present', async () => {
    (getProfile as vi.Mock).mockResolvedValue({ afterMealMinutes: 30 });
    const { result } = renderHook(() => useDefaultAfterMealMinutes(1));
    await waitFor(() => {
      expect(result.current).toBe(30);
    });
  });

  it('falls back to defaultAfterMealMinutes', async () => {
    (getProfile as vi.Mock).mockResolvedValue({ defaultAfterMealMinutes: 45 });
    const { result } = renderHook(() => useDefaultAfterMealMinutes(1));
    await waitFor(() => {
      expect(result.current).toBe(45);
    });
  });

  it('falls back to default_after_meal_minutes', async () => {
    (getProfile as vi.Mock).mockResolvedValue({ default_after_meal_minutes: 60 });
    const { result } = renderHook(() => useDefaultAfterMealMinutes(1));
    await waitFor(() => {
      expect(result.current).toBe(60);
    });
  });
});

