/// <reference types="vite/client" />

// файл: services/webapp/ui/src/vite-env.d.ts
declare global {
    interface ImportMetaEnv {
      readonly VITE_TELEGRAM_BOT: string;
    }
    interface ImportMeta {
      readonly env: ImportMetaEnv;
    }
  }
  
  export { };
  