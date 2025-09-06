import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';

import HelpHint from '../src/components/HelpHint';

describe('HelpHint', () => {
  afterEach(() => {
    cleanup();
  });

  const setup = () => render(<HelpHint label="ICR">Example</HelpHint>);

  it('shows tooltip on focus and hides on blur', async () => {
    setup();
    const button = screen.getByLabelText('ICR');
    expect(button.getAttribute('aria-label')).toBe('ICR');

    fireEvent.focus(button);
    expect((await screen.findByRole('tooltip')).textContent).toBe('Example');

    fireEvent.blur(button);
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('shows tooltip on click', async () => {
    setup();
    const button = screen.getByLabelText('ICR');
    fireEvent.click(button);
    expect((await screen.findByRole('tooltip')).textContent).toBe('Example');
  });

  it('closes tooltip on Escape key', async () => {
    setup();
    const button = screen.getByLabelText('ICR');

    fireEvent.focus(button);
    expect((await screen.findByRole('tooltip')).textContent).toBe('Example');

    fireEvent.keyDown(button, { key: 'Escape' });
    expect(screen.queryByRole('tooltip')).toBeNull();
  });
});
