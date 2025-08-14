// file: webapp/ui/src/main.tsx
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import { createRoot } from 'react-dom/client'

import App from './App'

// Базовые стили проекта
import './styles/theme.css'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <BrowserRouter basename={import.meta.env.BASE_URL}>
    <App />
  </BrowserRouter>
)
