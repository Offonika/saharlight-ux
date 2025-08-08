export {};

declare global {
  interface TelegramWebApp {
    sendData(data: string): void;
  }

  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

