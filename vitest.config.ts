import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    environment: 'jsdom',
  },
  resolve: {
    alias: [
      { find: '@sdk', replacement: path.resolve(__dirname, './libs/ts-sdk') },
      { find: '@', replacement: path.resolve(__dirname, './services/webapp/ui/src') },
    ],
  },
});
