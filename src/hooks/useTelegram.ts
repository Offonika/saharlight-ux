import { useEffect, useState } from 'react';

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        ready: () => void;
        close: () => void;
        expand: () => void;
        sendData: (data: string) => void;
        MainButton: {
          text: string;
          color: string;
          textColor: string;
          isVisible: boolean;
          isActive: boolean;
          setText: (text: string) => void;
          show: () => void;
          hide: () => void;
          onClick: (callback: () => void) => void;
        };
        BackButton: {
          isVisible: boolean;
          show: () => void;
          hide: () => void;
          onClick: (callback: () => void) => void;
        };
        themeParams: {
          bg_color?: string;
          text_color?: string;
          hint_color?: string;
          link_color?: string;
          button_color?: string;
          button_text_color?: string;
          secondary_bg_color?: string;
        };
        colorScheme: 'light' | 'dark';
        isExpanded: boolean;
        viewportHeight: number;
        viewportStableHeight: number;
        user?: {
          id: number;
          first_name: string;
          last_name?: string;
          username?: string;
        };
      };
    };
  }
}

export const useTelegram = () => {
  const [isReady, setIsReady] = useState(false);
  const [user, setUser] = useState<any>();
  const [colorScheme, setColorScheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      
      // Инициализация
      tg.ready();
      tg.expand();
      
      // Применение темы Telegram
      const themeParams = tg.themeParams;
      if (themeParams) {
        const root = document.documentElement;
        
        if (themeParams.bg_color) {
          root.style.setProperty('--tg-theme-bg-color', themeParams.bg_color);
        }
        if (themeParams.text_color) {
          root.style.setProperty('--tg-theme-text-color', themeParams.text_color);
        }
        if (themeParams.hint_color) {
          root.style.setProperty('--tg-theme-hint-color', themeParams.hint_color);
        }
        if (themeParams.link_color) {
          root.style.setProperty('--tg-theme-link-color', themeParams.link_color);
        }
        if (themeParams.button_color) {
          root.style.setProperty('--tg-theme-button-color', themeParams.button_color);
        }
        if (themeParams.button_text_color) {
          root.style.setProperty('--tg-theme-button-text-color', themeParams.button_text_color);
        }
        if (themeParams.secondary_bg_color) {
          root.style.setProperty('--tg-theme-secondary-bg-color', themeParams.secondary_bg_color);
        }
      }
      
      // Применение цветовой схемы
      if (tg.colorScheme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      
      setUser(tg.user);
      setColorScheme(tg.colorScheme);
      setIsReady(true);
    } else {
      // Fallback для разработки вне Telegram
      setIsReady(true);
    }
  }, []);

  const sendData = (data: any) => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.sendData(JSON.stringify(data));
    }
  };

  const showMainButton = (text: string, onClick: () => void) => {
    if (window.Telegram?.WebApp?.MainButton) {
      const mainButton = window.Telegram.WebApp.MainButton;
      mainButton.setText(text);
      mainButton.show();
      mainButton.onClick(onClick);
    }
  };

  const hideMainButton = () => {
    if (window.Telegram?.WebApp?.MainButton) {
      window.Telegram.WebApp.MainButton.hide();
    }
  };

  const showBackButton = (onClick: () => void) => {
    if (window.Telegram?.WebApp?.BackButton) {
      const backButton = window.Telegram.WebApp.BackButton;
      backButton.show();
      backButton.onClick(onClick);
    }
  };

  const hideBackButton = () => {
    if (window.Telegram?.WebApp?.BackButton) {
      window.Telegram.WebApp.BackButton.hide();
    }
  };

  return {
    isReady,
    user,
    colorScheme,
    sendData,
    showMainButton,
    hideMainButton,
    showBackButton,
    hideBackButton
  };
};