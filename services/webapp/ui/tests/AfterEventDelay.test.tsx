import React from 'react';
import { render, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import AfterEventDelay from '../src/features/reminders/components/AfterEventDelay';

function Wrapper({ onChange }: { onChange: (v: number) => void }) {
  const [value, setValue] = React.useState<number | undefined>();
  const handleChange = (v: number) => {
    onChange(v);
    setValue(v);
  };
  return <AfterEventDelay value={value} onChange={handleChange} />;
}

describe('AfterEventDelay', () => {
  afterEach(() => cleanup());

  it('calls onChange with preset value and activates button', () => {
    const onChange = vi.fn();
    const { getByRole } = render(<Wrapper onChange={onChange} />);
    const preset = getByRole('button', { name: /60/ });
    fireEvent.click(preset);
    expect(onChange).toHaveBeenCalledWith(60);
    expect(preset.getAttribute('aria-pressed')).toBe('true');
  });

  it('clears preset active state when manual value entered', () => {
    const onChange = vi.fn();
    const { getByRole } = render(<Wrapper onChange={onChange} />);
    const preset = getByRole('button', { name: /60/ });
    fireEvent.click(preset);
    const input = getByRole('spinbutton') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '65' } });
    expect(onChange).toHaveBeenLastCalledWith(65);
    expect(input.value).toBe('65');
    expect(preset.getAttribute('aria-pressed')).toBe('false');
  });
});
