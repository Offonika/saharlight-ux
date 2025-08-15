// file: services/webapp/ui/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

export default defineConfig(async ({ mode }) => {
  const plugins = [react()]
  if (mode === 'development') {
    const { componentTagger } = await import('lovable-tagger')
    plugins.push(componentTagger())
  }
  const base   = mode === 'development' ? '/' : '/ui/'  // dev → '/', prod → '/ui/'
  const port   = 5173                                   // или оставьте 8080 и укажите его в .lovable.yml
  return {
    base,
    plugins,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@sdk': path.resolve(__dirname, '../../../libs/ts-sdk'),
      },
    },
    server: { host: '::', port },
    build: {
      outDir: 'dist', // Явно задаём dist (по умолчанию и так dist)
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: [
              'react',
              'react-dom',
              'react-router-dom'
            ]
          }
        }
      }
    },
  }
})
