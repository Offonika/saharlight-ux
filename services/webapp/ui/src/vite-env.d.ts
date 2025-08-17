/// <reference types="vite/client" />

// файл: services/webapp/ui/src/vite-env.d.ts
declare global {
  interface ImportMetaEnv {
    readonly VITE_TELEGRAM_BOT?: string;
    readonly VITE_API_BASE?: string;
    readonly VITE_FORCE_LIGHT?: string;
  }
  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}

export {}
  