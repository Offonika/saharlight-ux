import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TimeInput from '../src/components/TimeInput';

describe('TimeInput', () => {
  it('renders native time input on non-iOS', () => {
    const { container } = render(<TimeInput value="" onChange={() => {}} />);
    expect(container.querySelector('input[type="time"]')).not.toBeNull();
  });

  it('renders masked text input when platform switches to iOS', () => {
    const originalTelegram = window.Telegram;
    const { container, rerender } = render(
      <TimeInput value="" onChange={() => {}} />,
    );

    expect(container.querySelector('input[type="time"]')).not.toBeNull();

    (window as any).Telegram = { WebApp: { platform: 'ios' } };
    rerender(<TimeInput value="" onChange={() => {}} />);

    const input = container.querySelector('input');
    expect(input?.getAttribute('type')).toBe('text');

    window.Telegram = originalTelegram;
  });
});
