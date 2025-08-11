// Root Vite config to point to the UI app without moving files
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

export default defineConfig({
  // Delegate to the UI folder as Vite root
  root: path.resolve(__dirname, 'webapp/ui'),
  plugins: [react()],
  server: {
    port: 8080,
  },
})
