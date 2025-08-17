import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Modal from './Modal'

describe('Modal', () => {
  it('sets ARIA attributes for title and content', () => {
    render(
      <Modal open onClose={() => {}} title="Test title">
        <p>Test content</p>
      </Modal>
    )
    const dialog = screen.getByRole('dialog')
    const heading = screen.getByRole('heading', { name: 'Test title' })
    const description = screen.getByText('Test content').parentElement as HTMLElement
    expect(dialog.getAttribute('aria-labelledby')).toBe(heading.id)
    expect(dialog.getAttribute('aria-describedby')).toBe(description.id)
  })
})
