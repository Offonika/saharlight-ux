import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import ProfileHelpSheet from '../src/components/ProfileHelpSheet';
import * as mobileHook from '@/hooks/use-mobile';

vi.mock('@/hooks/use-mobile', () => ({
  useIsMobile: vi.fn(() => false),
}));

describe('ProfileHelpSheet', () => {
  const openSheet = (therapy = 'tablets') => {
    render(<ProfileHelpSheet therapyType={therapy} />);
    fireEvent.click(screen.getAllByLabelText('Справка')[0]);
  };

  it('opens and closes on Escape key', () => {
    openSheet();
    expect(screen.getByRole('dialog')).toBeTruthy();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it("hides insulin section for tablets therapy", () => {
    openSheet('tablets');
    expect(screen.queryByText('Инсулин')).toBeNull();
    expect(screen.getByText('Цели сахара')).toBeTruthy();
  });
});
