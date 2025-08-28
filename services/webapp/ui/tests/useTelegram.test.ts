import { renderHook } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach } from 'vitest'
import { useTelegram } from '../src/hooks/useTelegram'

describe('useTelegram initData fallback', () => {
  beforeEach(() => {
    ;(window as any).Telegram = { WebApp: {} }
    localStorage.setItem('tg_init_data', 'stored-data')
  })

  afterEach(() => {
    delete (window as any).Telegram
    localStorage.clear()
  })

  it('reads initData from localStorage when tg.initData missing', () => {
    const { result } = renderHook(() => useTelegram(false))
    expect(result.current.initData).toBe('stored-data')
  })
})
