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

  it('returns default when afterMealMinutes is missing', async () => {
    (getProfile as vi.Mock).mockResolvedValue({});
    const { result } = renderHook(() => useDefaultAfterMealMinutes(1));
    await waitFor(() => {
      expect(result.current).toBe(120);
    });
  });

  it('returns default when profile is null', async () => {
    (getProfile as vi.Mock).mockResolvedValue(null);
    const { result } = renderHook(() => useDefaultAfterMealMinutes(1));
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(1);
      expect(result.current).toBe(120);
    });
  });
});

