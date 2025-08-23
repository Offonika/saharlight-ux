import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, expect, it, vi, afterEach } from 'vitest'
import Sheet from './Sheet'

afterEach(() => cleanup())

describe('Sheet', () => {
  it('renders content when open and returns null when closed', () => {
    const { rerender } = render(
      <Sheet open onClose={() => {}}>
        <p>Test content</p>
      </Sheet>
    )
    expect(screen.getByText('Test content')).toBeTruthy()
    rerender(
      <Sheet open={false} onClose={() => {}}>
        <p>Test content</p>
      </Sheet>
    )
    expect(screen.queryByText('Test content')).toBeNull()
  })

  it('calls onClose when Escape is pressed', () => {
    const onClose = vi.fn()
    render(
      <Sheet open onClose={onClose}>
        <button>btn</button>
      </Sheet>
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('traps focus with Tab and Shift+Tab', () => {
    render(
      <Sheet open onClose={() => {}}>
        <button>first</button>
        <button>last</button>
      </Sheet>
    )
    const buttons = screen.getAllByRole('button')
    buttons[1].focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(buttons[0])
    buttons[0].focus()
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(buttons[1])
  })

  it('calls onClose when clicking on the backdrop', () => {
    const onClose = vi.fn()
    const { container } = render(
      <Sheet open onClose={onClose}>
        <div>content</div>
      </Sheet>
    )
    const overlay = container.firstChild as HTMLElement
    fireEvent.mouseDown(overlay)
    expect(onClose).toHaveBeenCalled()
  })
})

