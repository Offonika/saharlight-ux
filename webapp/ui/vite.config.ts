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
      '@public': path.resolve(__dirname, '../public'),
    },
  },
  server: {
    fs: {
      allow: ['..'],
    },
  },
  build: {
    outDir: 'dist',    // кладём сборку в webapp/ui/dist
    emptyOutDir: true, // чистим dist перед сборкой
  },
})
