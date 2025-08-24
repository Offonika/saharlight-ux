import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

const navigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast: vi.fn() }) }))
vi.mock('@/contexts/telegram-context', () => ({ useTelegramContext: () => ({ user: { id: 1 } }) }))
vi.mock('@/api/profile', () => ({ getProfile: vi.fn(), saveProfile: vi.fn() }))

import Profile from './Profile'

afterEach(() => cleanup())

beforeEach(() => navigate.mockReset())

describe('Profile navigation buttons', () => {
  it('renders history and subscription buttons', async () => {
    render(<Profile />)
    expect(await screen.findByRole('button', { name: '📊 История' })).toBeTruthy()
    expect(await screen.findByRole('button', { name: '💳 Подписка' })).toBeTruthy()
  })

  it('navigates to history and subscription pages', async () => {
    render(<Profile />)
    fireEvent.click(await screen.findByRole('button', { name: '📊 История' }))
    expect(navigate).toHaveBeenCalledWith('/history')
    fireEvent.click(await screen.findByRole('button', { name: '💳 Подписка' }))
    expect(navigate).toHaveBeenCalledWith('/subscription')
  })
})
