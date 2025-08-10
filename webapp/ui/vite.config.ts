// file: webapp/ui/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

export default defineConfig({
  base: '/ui/',        // ассеты будут /ui/assets/...
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',    // кладём сборку в webapp/ui/dist
    emptyOutDir: true, // чистим dist перед сборкой
    rollupOptions: {
      // Не пытаемся обрабатывать внешние статические файлы корня webapp/
      external: ['/style.css', '/telegram-init.js'],
    },
  },
})
