import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import ProfileHelpSheet from '../src/components/ProfileHelpSheet';
import * as mobileHook from '@/hooks/use-mobile';

vi.mock('@/hooks/use-mobile', () => ({
  useIsMobile: vi.fn(() => false),
}));

describe('ProfileHelpSheet', () => {
  it('hides insulin sections for tablet therapy', () => {
    render(<ProfileHelpSheet therapyType="tablets" />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    expect(screen.queryByText(/ICR/)).toBeNull();
    expect(screen.queryByText(/Коэффициент коррекции/)).toBeNull();
    expect(screen.queryByText(/DIA/)).toBeNull();
    expect(screen.getByText(/Целевой уровень сахара/)).toBeTruthy();
  });

  it('closes on Escape key', () => {
    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    expect(screen.getByRole('dialog')).toBeTruthy();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('uses bottom sheet on mobile', () => {
    (mobileHook.useIsMobile as unknown as vi.Mock).mockReturnValue(true);
    render(<ProfileHelpSheet />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
    const content = screen.getByRole('dialog');
    expect(content.className).toContain('bottom-0');
  });
});
