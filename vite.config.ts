// vite.config.ts  (ветка lovable)
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

export default defineConfig(async ({ mode }) => {
  const plugins = [react()]
  if (mode === 'development') {
    const { componentTagger } = await import('lovable-tagger')
    plugins.push(componentTagger())
  }

  return {
    plugins,
    base: mode === 'development' ? '/' : '/ui/',
    resolve: {
      alias: {
        '@':   path.resolve(__dirname, './src'),
        '@sdk': path.resolve(__dirname, './libs/ts-sdk')
      }
    },
    server: {
      host: '::',
      port: 8080,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false
        }
      }
    },
    build: { outDir: 'dist' }
  }
})
