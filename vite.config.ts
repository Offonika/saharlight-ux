// Root Vite config to point to the UI app without moving files
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

export default defineConfig(async ({ mode }) => {
  const { componentTagger } = await import('lovable-tagger')

  return {
    // Delegate to the UI folder as Vite root
    root: path.resolve(__dirname, 'webapp/ui'),
    plugins: [react(), mode === 'development' && componentTagger()].filter(Boolean),
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'webapp/ui/src'),
      },
    },
    server: {
      host: '::',
      port: 8080,
    },
  }
})
