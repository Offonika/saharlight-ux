import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useState } from 'react'
import { SegmentedControl, type SegmentedItem } from './SegmentedControl'

const items: SegmentedItem[] = [
  { value: 'a', label: 'A' },
  { value: 'b', label: 'B' },
  { value: 'c', label: 'C' },
]

const Wrapper = () => {
  const [value, setValue] = useState('a')
  return <SegmentedControl value={value} onChange={setValue} items={items} />
}

describe('SegmentedControl', () => {
  it('uses radio roles and reflects selection with aria-checked', () => {
    render(<Wrapper />)
    expect(screen.getByRole('radiogroup')).toBeTruthy()
    const radios = screen.getAllByRole('radio')
    expect(radios).toHaveLength(3)
    expect(radios[0].getAttribute('aria-checked')).toBe('true')
    expect(radios[1].getAttribute('aria-checked')).toBe('false')
  })

  it('changes selection with arrow keys', () => {
    render(<Wrapper />)
    const radios = screen.getAllByRole('radio')
    radios[0].focus()
    fireEvent.keyDown(radios[0], { key: 'ArrowRight' })
    const updatedRadios = screen.getAllByRole('radio')
    expect(updatedRadios[1].getAttribute('aria-checked')).toBe('true')
    expect(updatedRadios[0].getAttribute('aria-checked')).toBe('false')
  })
})
