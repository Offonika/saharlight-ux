import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TimeInput from '../src/components/TimeInput';

describe('TimeInput', () => {
  it('renders native time input when Telegram is absent', () => {
    const win = window as typeof window & { Telegram?: unknown };
    const originalTelegram = win.Telegram;
    delete win.Telegram;

    const { container } = render(<TimeInput value="" onChange={() => {}} />);
    expect(container.querySelector('input[type="time"]')).not.toBeNull();

    win.Telegram = originalTelegram;
  });

  it('renders masked text input inside Telegram WebApp', () => {
    const win = window as typeof window & { Telegram?: unknown };
    const originalTelegram = win.Telegram;
    win.Telegram = { WebApp: {} };

    const { container } = render(<TimeInput value="" onChange={() => {}} />);
    const input = container.querySelector('input');
    expect(input?.getAttribute('type')).toBe('text');

    win.Telegram = originalTelegram;
  });
});

