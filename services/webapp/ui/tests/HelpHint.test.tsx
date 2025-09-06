import React from 'react';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, afterEach, vi } from 'vitest';

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

  it('uses mobile styles on small screens', async () => {
    const original = window.matchMedia;
    // @ts-expect-error -- jsdom
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === '(max-width: 640px)',
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    setup();
    const button = screen.getByLabelText('ICR');
    fireEvent.click(button);
    const tooltip = await screen.findByRole('tooltip');
    const content = tooltip.parentElement as HTMLElement;
    await waitFor(() =>
      expect(
        content.classList.contains('max-w-[calc(100vw-2rem)]'),
      ).toBe(true),
    );
    expect(content.getAttribute('data-side')).toBe('bottom');

    window.matchMedia = original;
  });
});
