import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ru from '../src/locales/ru';

import ProfileHelpSheet from '../src/components/ProfileHelpSheet';
import * as mobileHook from '@/hooks/use-mobile';

vi.mock('@/hooks/use-mobile', () => ({
  useIsMobile: vi.fn(() => false),
}));

describe('ProfileHelpSheet', () => {
  it.each([undefined, 'none', 'tablets'] as const)(
    'hides insulin section for %s therapy',
    (therapy) => {
      if (therapy === undefined) {
        render(<ProfileHelpSheet />);
      } else {
        render(<ProfileHelpSheet therapyType={therapy} />);
      }
      fireEvent.click(screen.getAllByLabelText('Справка')[0]);
      expect(screen.queryByText('Инсулин')).toBeNull();
      expect(screen.queryByText('Тип быстрого инсулина')).toBeNull();
      expect(screen.getByText('Цели сахара')).toBeTruthy();
    },
  );


  it('closes on Escape key', () => {
    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    expect(screen.getByRole('dialog')).toBeTruthy();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('renders focusable close button', () => {
    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    const closeBtn = screen.getByLabelText('Закрыть');
    closeBtn.focus();
    expect(document.activeElement).toBe(closeBtn);
    fireEvent.click(closeBtn);
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('uses bottom sheet on mobile', () => {
    (mobileHook.useIsMobile as unknown as vi.Mock).mockReturnValue(true);
    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    const content = screen.getByRole('dialog');
    expect(content.className).toContain('bottom-0');
  });

  it('allows multiple sections to be expanded', () => {
    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);

    fireEvent.click(screen.getByRole('button', { name: 'Цели сахара' }));
    fireEvent.click(screen.getByRole('button', { name: 'Прочее' }));

    expect(screen.getByText('Целевой уровень сахара')).toBeTruthy();
    expect(screen.getByText('Шаг округления')).toBeTruthy();
  });

  it.skip('renders unit without range when range translation is missing', () => {
    const original = ru.profileHelp.target.range;
    ru.profileHelp.target.range = '—';

    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Цели сахара' }));

    expect(screen.getByText(/Единицы:\s*ммоль\/л/)).toBeTruthy();
    expect(screen.queryByText(/Диапазон:\s*4.0–7.0/)).toBeNull();

    ru.profileHelp.target.range = original;
  });

  it.skip('renders range without unit when unit translation is missing', () => {
    const original = ru.profileHelp.target.unit;
    ru.profileHelp.target.unit = '—';

    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Цели сахара' }));

    expect(screen.getByText(/Диапазон:\s*4.0–7.0/)).toBeTruthy();
    expect(screen.queryByText(/Единицы:\s*ммоль\/л/)).toBeNull();

    ru.profileHelp.target.unit = original;
  });
});
