import React from 'react';
import { render, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

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
  useTelegramInitData: vi.fn(),
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

import Profile from '../src/pages/Profile';
import { saveProfile } from '../src/api/profile';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';

describe('Profile page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('blocks save without telegramId and shows toast', () => {
    useTelegramInitData.mockReturnValue(null);
    const { getByText } = render(<Profile />);
    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description: 'Некорректный ID пользователя',
        variant: 'destructive',
      }),
    );
  });

  it('blocks save with non-numeric id in initData and shows toast', () => {
    const invalidInitData = new URLSearchParams({
      user: JSON.stringify({ id: 'abc' }),
    }).toString();
    useTelegramInitData.mockReturnValue(invalidInitData);
    const { getByText } = render(<Profile />);
    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description: 'Некорректный ID пользователя',
        variant: 'destructive',
      }),
    );
  });

  it('blocks save with invalid numeric input and shows toast', () => {
    const validInitData = new URLSearchParams({
      user: JSON.stringify({ id: 123 }),
    }).toString();
    useTelegramInitData.mockReturnValue(validInitData);

    const { getByText, getByPlaceholderText } = render(<Profile />);
    const icrInput = getByPlaceholderText('12');
    fireEvent.change(icrInput, { target: { value: '-1' } });

    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description:
          'Проверьте, что все значения положительны, нижний порог меньше' +
          ' верхнего, а целевой уровень между ними',
        variant: 'destructive',
      }),
    );
  });

  it('blocks save when target is out of range and shows toast', () => {
    const validInitData = new URLSearchParams({
      user: JSON.stringify({ id: 123 }),
    }).toString();
    useTelegramInitData.mockReturnValue(validInitData);

    const { getByText, getByPlaceholderText } = render(<Profile />);
    const targetInput = getByPlaceholderText('6.0');
    fireEvent.change(targetInput, { target: { value: '12' } });

    fireEvent.click(getByText('Сохранить настройки'));
    expect(saveProfile).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description:
          'Проверьте, что все значения положительны, нижний порог меньше' +
          ' верхнего, а целевой уровень между ними',
        variant: 'destructive',
      }),
    );
  });
});
