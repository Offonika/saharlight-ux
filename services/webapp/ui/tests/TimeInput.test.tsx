import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TimeInput from '../src/components/TimeInput';

describe('TimeInput', () => {
  it('renders native time input on non-iOS', () => {
    const { container } = render(<TimeInput value="" onChange={() => {}} />);
    expect(container.querySelector('input[type="time"]')).not.toBeNull();
  });

  it('renders masked text input on iOS', async () => {
    const originalUA = navigator.userAgent;
    Object.defineProperty(navigator, 'userAgent', {
      value: 'iPhone',
      configurable: true,
    });
    vi.resetModules();
    const TimeInputIOS = (await import('../src/components/TimeInput')).default;
    const { container } = render(<TimeInputIOS value="" onChange={() => {}} />);
    const input = container.querySelector('input');
    expect(input?.getAttribute('type')).toBe('text');
    Object.defineProperty(navigator, 'userAgent', {
      value: originalUA,
      configurable: true,
    });
  });
});
