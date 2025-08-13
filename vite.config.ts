// services/webapp/ui/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // ⬇ dev-режим (Lovable, локально) → '/', прод → '/ui/'
  base: mode === 'development' ? '/' : '/ui/',
  server: { port: 5173 }
}))
