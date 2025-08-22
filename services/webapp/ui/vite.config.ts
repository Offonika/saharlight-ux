// file: services/webapp/ui/vite.config.ts
import { defineConfig, loadEnv, type Plugin } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'
import { readFile } from 'node:fs/promises'

function telegramInitPlugin(): Plugin {
  const shared = path.resolve(__dirname, '../public')
  const files = ['telegram-init.js']
  const serve = async (res: any, file: string) => {
    res.setHeader('Content-Type', 'application/javascript')
    res.end(await readFile(path.join(shared, file), 'utf8'))
  }
  return {
    name: 'telegram-init',
    async configureServer(server) {
      server.middlewares.use((req, res, next) => {
        for (const file of files) {
          if (req.url === `/${file}`) return serve(res, file)
        }
        return next()
      })
    },
    async generateBundle() {
      for (const file of files) {
        this.emitFile({
          type: 'asset',
          fileName: file,
          source: await readFile(path.join(shared, file), 'utf8'),
        })
      }
    },
  }
}

export default defineConfig(async ({ mode, command }) => {
  if (command === 'build' && mode === 'development') {
    throw new Error('build mode "development" is not allowed')
  }
  const env = loadEnv(mode, process.cwd(), '')
  const plugins = [react(), telegramInitPlugin()]
  if (mode === 'development') {
    const { componentTagger } = await import('lovable-tagger')
    plugins.push(componentTagger())
  }
  const rawBase = env.VITE_BASE_URL ?? (mode === 'development' ? '/' : '/ui/')
  const base = rawBase.endsWith('/') ? rawBase : `${rawBase}/`
  const port = 5173 // или оставьте 8080 и укажите его в .lovable.yml
  const rollupOptions = {
    ...(mode === 'development' ? { treeshake: false } : {}),
    external: [
      'telegram-init.js',
      '/telegram-init.js',
      `${base}telegram-init.js`,
    ],
    input: {
      main: path.resolve(__dirname, 'index.html'),
      'telegram-theme': path.resolve(
        __dirname,
        './src/lib/telegram-theme.ts',
      ),
    },
    preserveEntrySignatures: 'strict',
    output: {
      entryFileNames: (chunk) =>
        chunk.name === 'telegram-theme'
          ? 'assets/telegram-theme.js'
          : 'assets/[name]-[hash].js',
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
      },
    },
    server: { host: '::', port },
    build: {
      outDir: 'dist', // Явно задаём dist (по умолчанию и так dist)
      minify: mode === 'development' ? false : 'esbuild',
      rollupOptions,
      minifyInternalExports: false,
    },
  }
})
