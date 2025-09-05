import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/features/profile/api', () => ({
  getProfile: vi.fn(),
}));

const toast = vi.fn();
vi.mock('../src/hooks/use-toast', () => ({
  useToast: () => ({ toast }),
}));

import { useDefaultAfterMealMinutes } from '../src/features/profile/hooks';
import { getProfile } from '../src/features/profile/api';
import { useTranslation } from '../src/i18n';

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

  it('returns null when afterMealMinutes is missing', async () => {
    (getProfile as vi.Mock).mockResolvedValue({});
    const { result } = renderHook(() => useDefaultAfterMealMinutes(1));
    await waitFor(() => {
      expect(result.current).toBeNull();
    });
  });

  it('shows toast when profile is missing', async () => {
    (getProfile as vi.Mock).mockRejectedValue(new Error('Профиль не найден'));
    renderHook(() => useDefaultAfterMealMinutes(1));
    const { t } = useTranslation();
    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: t('profile.notFound'),
          variant: 'destructive',
        }),
      );
    });
  });
});

