import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';

import HelpHint from '../src/components/HelpHint';
import { TooltipProvider } from '../src/components/ui/tooltip';

describe('HelpHint', () => {
  afterEach(() => {
    cleanup();
  });

  const setup = () =>
    render(
      <TooltipProvider delayDuration={0}>
        <HelpHint label="ICR">Example</HelpHint>
      </TooltipProvider>,
    );

  it('shows tooltip on focus and closes on Escape', async () => {
    setup();
    const button = screen.getByLabelText('ICR');

    fireEvent.focus(button);
    expect((await screen.findByRole('tooltip')).textContent).toBe('Example');

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('tooltip')).toBeNull();
  });
});
