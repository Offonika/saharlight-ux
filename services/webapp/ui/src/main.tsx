import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import { setTelegramInitData } from '@/lib/telegram-auth'

function initTelegram(): void {
  try {
    const globalData = (window as any)?.Telegram?.WebApp?.initData
    if (globalData) {
      setTelegramInitData(globalData)
      return
    }
    const hash = window.location.hash.startsWith('#')
      ? window.location.hash.slice(1)
      : window.location.hash
    const tgWebAppData = new URLSearchParams(hash).get('tgWebAppData')
    if (tgWebAppData) {
      setTelegramInitData(tgWebAppData)
    }
  } catch {
    /* ignore */
  }
}

initTelegram()

if (import.meta.env.DEV) {
  import('./api/mock-server')
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
