// file: webapp/ui/src/main.tsx
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import { createRoot } from 'react-dom/client'

import App from './App'
import { TelegramProvider } from '@/contexts/TelegramProvider'

// Базовые стили проекта
import './styles/theme.css'
import './index.css'

const tgStartParam = new URLSearchParams(window.location.search).get(
  'tgWebAppStartParam',
)
if (tgStartParam) {
  const win = window as { tgWebAppStartParam?: string }
  win.tgWebAppStartParam = tgStartParam
}

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error('Root element with id "root" not found')
}

const basename = import.meta.env.BASE_URL.replace(/\/$/, '')

createRoot(rootElement).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <TelegramProvider>
        <App />
      </TelegramProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
