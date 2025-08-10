import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './styles/theme.css'
import './index.css'
import './styles/theme.css'
import '@public/telegram-init.js'

createRoot(document.getElementById("root")!).render(<App />);
