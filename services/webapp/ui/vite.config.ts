// file: services/webapp/ui/vite.config.ts
import { defineConfig, type ConfigEnv, type PluginOption } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { componentTagger } from 'lovable-tagger'
import path from 'path'

export default defineConfig(({ mode }: ConfigEnv) => {
  const plugins: PluginOption[] = [...react()]
  if (mode === 'development') {
    plugins.push(componentTagger())
  }
  const base = mode === 'development' ? '/' : '/ui/'
  const port = 5173
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
      outDir: 'dist',
      minify: false,
      rollupOptions: {
        treeshake: false,
        input: {
          main: path.resolve(__dirname, 'index.html'),
          'telegram-theme': path.resolve(
            __dirname,
            './src/lib/telegram-theme.ts',
          ),
        },
        output: {
          entryFileNames: (chunk: { name: string }) =>
            chunk.name === 'telegram-theme'
              ? 'assets/telegram-theme.js'
              : 'assets/[name]-[hash].js',
          exports: 'named' as const,
          manualChunks: {
            vendor: ['react', 'react-dom', 'react-router-dom'],
          },
        },
      },
    },
  }
})
