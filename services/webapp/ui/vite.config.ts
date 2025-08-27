// file: services/webapp/ui/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'
import { fileURLToPath } from 'url'
import tsconfigPaths from 'vite-tsconfig-paths'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const sdkPath = path.resolve(__dirname, '../../../libs/ts-sdk')

export default defineConfig(async ({ mode }) => {
  const plugins = [react(), tsconfigPaths()]
  if (mode === 'development') {
    const { componentTagger } = await import('lovable-tagger')
    plugins.push(componentTagger())
  }
  const base   = mode === 'development' ? '/' : '/ui/'  // dev → '/', prod → '/ui/'
  const port   = 5173                                   // или оставьте 8080 и укажите его в .lovable.yml
  return {
    base: '/ui/',
    plugins,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@sdk': sdkPath,
      },
    },
    server: { host: '::', port: 8080, fs: { allow: [sdkPath] } },
    build: { outDir: 'dist' }, // Явно задаём dist (по умолчанию и так dist)
  }
})
