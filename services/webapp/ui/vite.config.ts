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

  return {
    base: '/ui/',
    plugins,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@sdk': path.resolve(__dirname, '../../../libs/ts-sdk'),
      },
    },
    server: { host: '::', port: 8080 },
    build: { outDir: 'dist' }, // Явно задаём dist (по умолчанию и так dist)
  }
})
