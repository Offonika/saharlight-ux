import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

const toast = vi.fn();

vi.mock('../src/api/profile', () => ({
  saveProfile: vi.fn(),
}));

vi.mock('../src/hooks/use-toast', () => ({
  useToast: () => ({ toast }),
}));

vi.mock('../src/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: null }),
}));

vi.mock('../src/hooks/useTelegramInitData', () => ({
  useTelegramInitData: () => '',
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

import Profile from '../src/pages/Profile';
import { saveProfile } from '../src/api/profile';

describe('Profile page', () => {
  it('blocks save without telegramId and shows toast', () => {
    const { getByText } = render(<Profile />);
    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description: 'Не удалось определить пользователя',
        variant: 'destructive',
      }),
    );
  });
});
