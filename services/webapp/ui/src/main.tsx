// file: webapp/ui/src/main.tsx
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import { createRoot } from 'react-dom/client'

import App from './App'
import { TelegramProvider } from '@/contexts/TelegramProvider'

// Базовые стили проекта
import './styles/theme.css'
import './index.css'

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error('Root element with id "root" not found')
}

createRoot(rootElement).render(
  <React.StrictMode>
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <TelegramProvider>
        <App />
      </TelegramProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
