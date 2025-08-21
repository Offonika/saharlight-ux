import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { tgFetch } from "../lib/tgFetch";
import applyTelegramTheme, {
  type Scheme,
  type TelegramWebApp as TelegramWebAppBase,
} from "../lib/telegram-theme";

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

interface TelegramWebApp extends TelegramWebAppBase {
  expand?: () => void;
  ready?: () => void;
  initDataUnsafe?: { user?: TelegramUser };
  initData?: string;
  onEvent?: (eventType: string, handler: () => void) => void;
  offEvent?: (eventType: string, handler: () => void) => void;
  MainButton?: MainButton;
  BackButton?: BackButton;
  sendData?: (data: string) => void;
}

interface TelegramWindow extends Window {
  Telegram?: { WebApp?: TelegramWebApp };
}

interface TelegramError {
  code: string;
  message?: string;
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
  const [error, setError] = useState<TelegramError | null>(null);
  const [colorScheme, setScheme] = useState<Scheme>("light");
  const mainClickRef = useRef<(() => void) | null>(null);
  const backClickRef = useRef<(() => void) | null>(null);

  const applyTheme = useCallback(
    (src: TelegramWebApp | null, ignoreScheme = false) => {
      const scheme = applyTelegramTheme(src, ignoreScheme);
      setScheme(scheme);
    },
    [],
  );

  useEffect(() => {
    let cancelled = false;
    if (!tg) {
      console.warn("[TG] not in Telegram, enabling dev fallback");
      applyTheme(null, forceLight);
      setError({ code: "no-user" });
      setReady(true);
      return () => {
        cancelled = true;
      };
    }
    try {
      tg.expand?.();
      tg.ready?.();
      applyTheme(tg, forceLight);
      const params = new URLSearchParams(tg.initData ?? "");
      const userRaw = params.get("user");
      let userObj: TelegramUser | null = null;
      try {
        userObj = userRaw ? JSON.parse(userRaw) : null;
      } catch (err) {
        console.warn("[TG] failed to parse initData user", err);
      }
      const finalUser = tg.initDataUnsafe?.user ?? userObj;
      setUser(finalUser);
      setError(null);
      if (!finalUser?.id) {
        console.warn("[TG] failed to get user ID", {
          initData: tg.initData,
          initDataUnsafe: tg.initDataUnsafe,
        });
        const tryFallback = async () => {
          await new Promise((r) => setTimeout(r, 100));
          let retryUser = tg.initDataUnsafe?.user;
          if (!retryUser?.id) {
            const again = new URLSearchParams(tg.initData ?? "").get("user");
            try {
              retryUser = again ? JSON.parse(again) : null;
            } catch {
              /* ignore */
            }
          }
          if (retryUser?.id) {
            if (cancelled) return;
            setUser(retryUser);
            return;
          }
          if (document.cookie) {
            try {
              const resp = await tgFetch("/api/profile/self", {
                credentials: "include",
              });
              const data = await resp.json().catch(() => null);
              if (data?.id) {
                if (cancelled) return;
                setUser(data);
                return;
              }
            } catch (err) {
              console.warn("[TG] profile fetch failed", err);
            }
          }
          if (cancelled) return;
          setError({ code: "no-user" });
        };
        void tryFallback();
      }
      setReady(true);
      const onTheme = () => applyTheme(tg, forceLight);
      tg.onEvent?.("themeChanged", onTheme);
      return () => {
        cancelled = true;
        tg.offEvent?.("themeChanged", onTheme);
        if (mainClickRef.current) tg.MainButton?.offClick?.(mainClickRef.current);
        if (backClickRef.current) tg.BackButton?.offClick?.(backClickRef.current);
      };
    } catch (e) {
      console.error("[TG] init error:", e);
      setError({
        code: "unknown",
        message: e instanceof Error ? e.message : String(e),
      });
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
    error,
    sendData,
    showMainButton,
    hideMainButton,
    showBackButton,
    hideBackButton,
  };
};
