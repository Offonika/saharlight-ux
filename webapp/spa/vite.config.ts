// webapp/spa/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/ui/',        // ассеты будут /ui/assets/...
  plugins: [react()],
  build: {
    outDir: '../ui',   // кладём сборку в webapp/ui
    emptyOutDir: true, // чистим ui перед сборкой
  },
})
