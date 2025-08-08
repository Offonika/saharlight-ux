// webapp/ui/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/ui/',         // КРИТИЧНО: чтобы index.html ссылался на /ui/assets/*
  plugins: [react()],
  build: {
    outDir: '.',        // билд в webapp/ui (как у вас)
    emptyOutDir: false, // не вычищать всё, если там есть ручные файлы
  },
})
