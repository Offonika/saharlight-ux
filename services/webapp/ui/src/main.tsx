// file: webapp/ui/src/main.tsx
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

// Базовые стили проекта (подключаем ОДИН раз)
import './styles/theme.css'
import './index.css'

// Если стили ux-кита не тянутcя автоматически его index.ts, раскомментируй:
// import '../../ux-kit/src/styles/theme.css'

createRoot(document.getElementById('root')!).render(<App />)
