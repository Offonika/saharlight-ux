import React from 'react';
import { render, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const toast = vi.fn();

vi.mock('../src/api/profile', () => ({
  saveProfile: vi.fn(),
  getProfile: vi.fn(),
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
import { saveProfile, getProfile } from '../src/api/profile';
import { useTelegramInitData } from '../src/hooks/useTelegramInitData';
import { parseProfile } from '../src/pages/Profile';

describe('Profile page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getProfile as vi.Mock).mockResolvedValue({
      telegramId: 0,
      icr: 12,
      cf: 2.5,
      target: 6,
      low: 4,
      high: 10,
    });
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


  it('loads profile on mount and updates form', async () => {
    const validInitData = new URLSearchParams({
      user: JSON.stringify({ id: 123 }),
    }).toString();
    useTelegramInitData.mockReturnValue(validInitData);
    (getProfile as vi.Mock).mockResolvedValue({
      telegramId: 123,
      icr: 15,
      cf: 3,
      target: 5,
      low: 3,
      high: 8,
    });

    const { getByPlaceholderText } = render(<Profile />);
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });
    expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('15');
    expect((getByPlaceholderText('2.5') as HTMLInputElement).value).toBe('3');
  });

  it('shows toast when profile load fails', async () => {
    const validInitData = new URLSearchParams({
      user: JSON.stringify({ id: 123 }),
    }).toString();
    useTelegramInitData.mockReturnValue(validInitData);
    (getProfile as vi.Mock).mockRejectedValue(new Error('load failed'));

    const { getByPlaceholderText } = render(<Profile />);
    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledWith(123);
    });
    expect(toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Ошибка',
        description: 'load failed',
        variant: 'destructive',
      }),
    );
    expect((getByPlaceholderText('12') as HTMLInputElement).value).toBe('12');
  });
});

describe('parseProfile', () => {
  it('parses values with commas', () => {
    expect(
      parseProfile({
        icr: '1,5',
        cf: '2,5',
        target: '5,5',
        low: '4,4',
        high: '10,1',
      }),
    ).toEqual({ icr: 1.5, cf: 2.5, target: 5.5, low: 4.4, high: 10.1 });
  });
});
