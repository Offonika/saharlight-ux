// file: services/webapp/ui/vite.config.ts
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'
import { readFile } from 'node:fs/promises'

function telegramInitPlugin(): Plugin {
  const shared = path.resolve(__dirname, '../public')
  const serve = async (res: any, file: string) => {
    res.setHeader('Content-Type', 'application/javascript')
    res.end(await readFile(path.join(shared, file), 'utf8'))
  }
  return {
    name: 'telegram-init',
    async configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === '/telegram-init.js') return serve(res, 'telegram-init.js')
        if (req.url === '/assets/telegram-theme.js')
          return serve(res, 'assets/telegram-theme.js')
        return next()
      })
    },
    async generateBundle() {
      for (const file of ['telegram-init.js', 'assets/telegram-theme.js']) {
        this.emitFile({
          type: 'asset',
          fileName: file,
          source: await readFile(path.join(shared, file), 'utf8'),
        })
      }
    },
  }
}

export default defineConfig(async ({ mode }) => {
  const plugins = [react(), telegramInitPlugin()]
  if (mode === 'development') {
    const { componentTagger } = await import('lovable-tagger')
    plugins.push(componentTagger())
  }
  const base   = mode === 'development' ? '/' : '/ui/'  // dev → '/', prod → '/ui/'
  const port   = 5173                                   // или оставьте 8080 и укажите его в .lovable.yml
  const rollupOptions = {
    ...(mode === 'development' ? { treeshake: false } : {}),
    external: ['telegram-init.js', '/telegram-init.js', '/ui/telegram-init.js'],
    input: {
      main: path.resolve(__dirname, 'index.html'),
      'telegram-theme': path.resolve(
        __dirname,
        './src/lib/telegram-theme.ts',
      ),
    },
    output: {
      entryFileNames: (chunk) =>
        chunk.name === 'telegram-theme'
          ? 'assets/telegram-theme.js'
          : 'assets/[name]-[hash].js',
      exports: 'named',
      manualChunks: {
        vendor: ['react', 'react-dom', 'react-router-dom'],
      },
    },
  }
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
      minify: mode === 'development' ? false : 'esbuild',
      rollupOptions,
    },
  }
})
