// file: apps/web/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

export default defineConfig(async ({ mode }) => {
  const { componentTagger } = await import('lovable-tagger')

  return {
    base: '/ui/',
    plugins: [react(), mode === 'development' && componentTagger()].filter(Boolean),
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@ux': path.resolve(__dirname, '../ux-kit/src'), // ← сюда будет синкаться дизайн
      },
    },
    server: {
      host: '::',
      port: 8080,
    },
  }
})
