import React from 'react'
import { describe, expect, test, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import PaywallGuard from '@/features/paywall/PaywallGuard'
import '@testing-library/jest-dom/vitest'

describe('PaywallGuard', () => {
  test('renders children for pro user', () => {
    render(
      <MemoryRouter>
        <PaywallGuard status="pro" mode="soft">
          <div>content</div>
        </PaywallGuard>
      </MemoryRouter>
    )
    expect(screen.getByText('content')).toBeInTheDocument()
  })

  test('shows teaser in soft mode for free user', () => {
    const log = vi.spyOn(console, 'log').mockImplementation(() => {})
    render(
      <MemoryRouter>
        <PaywallGuard status="free" mode="soft">
          <div>content</div>
        </PaywallGuard>
      </MemoryRouter>
    )
    expect(screen.getByTestId('paywall-teaser')).toBeInTheDocument()
    expect(log).toHaveBeenCalledWith('[metrics] encountered paywall')
    log.mockRestore()
  })
})
