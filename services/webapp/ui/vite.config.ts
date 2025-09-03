// file: services/webapp/ui/vite.config.ts
import { defineConfig, loadEnv, type Plugin, type ViteDevServer } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'
import { readFile } from 'node:fs/promises'
import { ServerResponse } from 'node:http'

function telegramInitPlugin(): Plugin {
  const shared = path.resolve(__dirname, '../public')
  const files = ['telegram-init.js', 'telegram-theme.js']
  const telegramInitPath = path.join(shared, 'telegram-init.js')
  const themeId = './telegram-theme.js'

  const serve = async (res: ServerResponse, file: string) => {
    res.setHeader('Content-Type', 'application/javascript')
    res.end(await readFile(path.join(shared, file), 'utf8'))
  }

  return {
    name: 'telegram-init',

    // В dev: перехватываем запросы на /ui/telegram-*.js и отдаём из public/
    async configureServer(server: ViteDevServer) {
      server.middlewares.use((req, res, next) => {
        const url = req.url ?? ''
        if (url === '/ui/telegram-init.js')  return serve(res, 'telegram-init.js')
        if (url === '/ui/telegram-theme.js') return serve(res, 'telegram-theme.js')
        return next()
      })
    },

    // Резолв только для статического импорта init (если где-то используется)
    resolveId(id, importer) {
      if (id === 'telegram-init.js' || id === '/ui/telegram-init.js' || id === '/telegram-init.js') {
        return telegramInitPath
      }
      // динамический импорт темы из init оставляем внешним модулем
      if (importer === telegramInitPath && id === themeId) {
        return { id: themeId, external: true }
      }
      return null
    },

    // Подхватываем содержимое init при статическом импорте (опционально)
    async load(id) {
      if (id === telegramInitPath) return await readFile(telegramInitPath, 'utf8')
      return null
    },

    // В prod: кладём telegram-*.js в КОРЕНЬ dist (dist/telegram-*.js),
    // чтобы URL /ui/telegram-*.js резолвился через Alias /ui/ → dist/
    async generateBundle() {
      for (const file of files) {
        this.emitFile({
          type: 'asset',
          fileName: file, // ⬅️ ВАЖНО: без префикса ui/
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
  const rawBase = env.VITE_BASE_URL ?? (mode === 'development' ? '/' : '/ui/')
  const base = rawBase.endsWith('/') ? rawBase : `${rawBase}/`

  const plugins = [react(), telegramInitPlugin()]
  if (mode === 'development') {
    const { componentTagger } = await import('lovable-tagger')
    plugins.push(componentTagger())
  }

  return {
    base,
    plugins,
    resolve: {
      alias: [
        { find: '@sdk', replacement: path.resolve(__dirname, '../../../libs/ts-sdk') },
        { find: '@', replacement: path.resolve(__dirname, './src') },
      ],
    },
    server: { host: '::', port: 5173 },

    build: {
      outDir: 'dist',
      minify: false, // or 'esbuild'
      cssMinify: false,
      minifyInternalExports: false,
      sourcemap: false,
      rollupOptions: {
        ...(mode === 'development' ? { treeshake: false } : {}),
        input: {
          main: path.resolve(__dirname, 'index.html'),
          timezone: path.resolve(__dirname, 'src/pages/timezone.html'),
        },
        preserveEntrySignatures: 'strict',
        output: {
          entryFileNames: 'assets/[name]-[hash].js',
          manualChunks: {
            vendor: ['react', 'react-dom', 'react-router-dom'],
          },
        },
      },
    },
  }
})
