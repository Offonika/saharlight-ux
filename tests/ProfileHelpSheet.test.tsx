import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import ProfileHelpSheet from '../services/webapp/ui/src/components/ProfileHelpSheet';

vi.mock('@/hooks/use-mobile', () => ({
  useIsMobile: () => false,
}));

describe('ProfileHelpSheet', () => {
  it('opens and closes the help sheet', () => {
    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    expect(screen.getByRole('dialog')).toBeTruthy();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it("hides 'Инсулин' section for tablets therapy", () => {
    render(<ProfileHelpSheet therapyType="tablets" />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    expect(screen.queryByText('Инсулин')).toBeNull();
    expect(screen.getByText('Цели сахара')).toBeTruthy();
  });

  it('omits unit and range for rapid insulin type', () => {
    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Инсулин' }));
    const item = screen.getByText('Тип быстрого инсулина').closest('li');
    expect(item).not.toBeNull();
    const utils = within(item as HTMLElement);
    expect(utils.queryByText(/Единицы/)).toBeNull();
    expect(utils.queryByText(/Диапазон/)).toBeNull();
  });
});

