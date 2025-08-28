import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getDevInitData } from "../lib/telegram-auth";

type Scheme = "light" | "dark";

interface TelegramUser {
  id: number;
  is_bot?: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
  is_premium?: boolean;
  added_to_attachment_menu?: boolean;
  allows_write_to_pm?: boolean;
}

interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

interface MainButton {
  setText: (text: string) => void;
  onClick: (handler: () => void) => void;
  offClick: (handler: () => void) => void;
  show: () => void;
  hide: () => void;
}

interface BackButton {
  onClick: (handler: () => void) => void;
  offClick: (handler: () => void) => void;
  show: () => void;
  hide: () => void;
}

interface TelegramWebApp {
  expand?: () => void;
  ready?: () => void;
  colorScheme?: Scheme;
  themeParams?: ThemeParams;
  user?: TelegramUser;
  initDataUnsafe?: { user?: TelegramUser };
  setBackgroundColor?: (color: string) => void;
  setHeaderColor?: (color: string) => void;
  onEvent?: (eventType: string, handler: () => void) => void;
  offEvent?: (eventType: string, handler: () => void) => void;
  MainButton?: MainButton;
  BackButton?: BackButton;
  sendData?: (data: string) => void;
}

interface TelegramWindow extends Window {
  Telegram?: { WebApp?: TelegramWebApp };
}

export const useTelegram = (
  forceLight: boolean = import.meta.env.VITE_FORCE_LIGHT === "true",
) => {
  const tg = useMemo<TelegramWebApp | null>(
    () => (window as TelegramWindow)?.Telegram?.WebApp ?? null,
    [],
  );
  const [isReady, setReady] = useState<boolean>(false);
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [colorScheme, setScheme] = useState<Scheme>("light");
  const mainClickRef = useRef<(() => void) | null>(null);
  const backClickRef = useRef<(() => void) | null>(null);

  // Конвертация hex в HSL
  const hexToHsl = useCallback((hex: string): string => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return hex;

    const r = parseInt(result[1], 16) / 255;
    const g = parseInt(result[2], 16) / 255;
    const b = parseInt(result[3], 16) / 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h = 0,
      s = 0,
      l = (max + min) / 2;

    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r:
          h = (g - b) / d + (g < b ? 6 : 0);
          break;
        case g:
          h = (b - r) / d + 2;
          break;
        case b:
          h = (r - g) / d + 4;
          break;
      }
      h /= 6;
    }

    return `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
  }, []);

  const applyTheme = useCallback(
    (src: TelegramWebApp | null, ignoreScheme = false) => {
      const root = document.documentElement;
      const p = src?.themeParams ?? {};

      if (ignoreScheme) {
        // Remove Telegram theme overrides to fall back to default light colors
        const themeKeys = [
          "--tg-theme-bg-color",
          "--tg-theme-text-color",
          "--tg-theme-hint-color",
          "--tg-theme-link-color",
          "--tg-theme-button-color",
          "--tg-theme-button-text-color",
          "--tg-theme-secondary-bg-color",
        ];
        themeKeys.forEach((k) => root.style.removeProperty(k));
        root.classList.remove("dark");
        root.classList.add("light");
        root.style.colorScheme = "light";
        setScheme("light");
        src?.setBackgroundColor?.("#ffffff");
        src?.setHeaderColor?.("#ffffff");
      } else {
        // Применяем Telegram цвета в HSL формате
        if (p.bg_color)
          root.style.setProperty("--tg-theme-bg-color", hexToHsl(p.bg_color));
        if (p.text_color)
          root.style.setProperty(
            "--tg-theme-text-color",
            hexToHsl(p.text_color),
          );
        if (p.hint_color)
          root.style.setProperty(
            "--tg-theme-hint-color",
            hexToHsl(p.hint_color),
          );
        if (p.link_color)
          root.style.setProperty(
            "--tg-theme-link-color",
            hexToHsl(p.link_color),
          );
        if (p.button_color)
          root.style.setProperty(
            "--tg-theme-button-color",
            hexToHsl(p.button_color),
          );
        if (p.button_text_color)
          root.style.setProperty(
            "--tg-theme-button-text-color",
            hexToHsl(p.button_text_color),
          );
        if (p.secondary_bg_color)
          root.style.setProperty(
            "--tg-theme-secondary-bg-color",
            hexToHsl(p.secondary_bg_color),
          );

        const isDark = src?.colorScheme === "dark";
        root.classList.toggle("dark", isDark);
        root.classList.toggle("light", !isDark);
        root.style.colorScheme = src?.colorScheme || "light";
        setScheme(src?.colorScheme ?? "light");
      }
    },
    [hexToHsl],
  );

  useEffect(() => {
    const createDevUser = (): TelegramUser => {
      let devUser: TelegramUser | null = null;

      const initData = getDevInitData();
      if (initData) {
        const userStr = new URLSearchParams(initData).get("user");
        if (userStr) {
          try {
            devUser = JSON.parse(userStr);
            console.log("[TG] parsed dev user from initData:", devUser);
          } catch (e) {
            console.error("[TG] failed to parse dev user:", e);
          }
        }
      }

      // If no user from initData, create fallback test user
      if (!devUser) {
        const devUserId = import.meta.env.VITE_DEV_USER_ID || "12345";
        devUser = {
          id: parseInt(devUserId, 10),
          first_name: "Test",
          last_name: "User",
          username: "testuser",
          language_code: "ru",
        };
        console.log("[TG] created fallback dev user:", devUser);
      }

      return devUser;
    };

    if (!tg) {
      console.warn("[TG] not in Telegram, enabling dev fallback");

      // In development mode, create fallback user
      if (import.meta.env.MODE !== "production") {
        setUser(createDevUser());
      }

      applyTheme(null, forceLight);
      setReady(true);
      return;
    }

    try {
      tg.expand?.();
      tg.ready?.();
      applyTheme(tg, forceLight);

      const tgUser = tg.user || tg.initDataUnsafe?.user;
      if (!tgUser && import.meta.env.MODE !== "production") {
        console.warn("[TG] no user in Telegram WebApp, creating dev fallback");
        setUser(createDevUser());
      } else {
        setUser(tgUser ?? null);
      }

      setReady(true);
      const onTheme = () => applyTheme(tg, forceLight);
      tg.onEvent?.("themeChanged", onTheme);
      return () => {
        tg.offEvent?.("themeChanged", onTheme);
        if (mainClickRef.current)
          tg.MainButton?.offClick?.(mainClickRef.current);
        if (backClickRef.current)
          tg.BackButton?.offClick?.(backClickRef.current);
      };
    } catch (e) {
      console.error("[TG] init error:", e);
      setReady(true);
    }
  }, [tg, applyTheme, forceLight]);

  const sendData = (data: unknown) => tg?.sendData?.(JSON.stringify(data));

  const showMainButton = (text: string, onClick: () => void) => {
    if (!tg?.MainButton) return;
    if (mainClickRef.current) tg.MainButton.offClick?.(mainClickRef.current);
    mainClickRef.current = onClick;
    tg.MainButton.setText(text);
    tg.MainButton.onClick(onClick);
    tg.MainButton.show();
  };
  const hideMainButton = () => tg?.MainButton?.hide?.();

  const showBackButton = (onClick: () => void) => {
    if (!tg?.BackButton) return;
    if (backClickRef.current) tg.BackButton.offClick?.(backClickRef.current);
    backClickRef.current = onClick;
    tg.BackButton.onClick(onClick);
    tg.BackButton.show();
  };
  const hideBackButton = () => tg?.BackButton?.hide?.();

  return {
    tg,
    isReady,
    user,
    colorScheme,
    sendData,
    showMainButton,
    hideMainButton,
    showBackButton,
    hideBackButton,
    isTelegram: Boolean(tg),
  };
};
