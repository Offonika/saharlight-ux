import React from 'react';
import { render, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach, vi } from 'vitest';

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: { sugar: 0, breadUnits: 0, insulin: 0 }, isLoading: false, error: null }),
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock('../src/hooks/useTelegram', () => ({
  useTelegram: () => ({ user: { id: 1, first_name: 'Test' } }),
}));

import Home from '../src/pages/Home';

describe('Home page', () => {
  afterEach(() => cleanup());

  it('renders all menu tiles', () => {
    const { getByText } = render(<Home />);
    expect(getByText('История')).toBeTruthy();
    expect(getByText('Профиль')).toBeTruthy();
    expect(getByText('Напоминания')).toBeTruthy();
    expect(getByText('Аналитика')).toBeTruthy();
    expect(getByText('Подписка')).toBeTruthy();
  });
});

