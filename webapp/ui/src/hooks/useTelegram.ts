import { useEffect, useMemo, useRef, useState } from "react";

type Scheme = "light" | "dark";

export const useTelegram = (
  forceLight: boolean = import.meta.env.VITE_FORCE_LIGHT === "true",
) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tg = useMemo(() => (window as any)?.Telegram?.WebApp ?? null, []);
  const [isReady, setReady] = useState<boolean>(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [user, setUser] = useState<any>(null);
  const [colorScheme, setScheme] = useState<Scheme>("light");
  const mainClickRef = useRef<(() => void) | null>(null);
  const backClickRef = useRef<(() => void) | null>(null);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const applyTheme = (src: any, ignoreScheme = false) => {
    const root = document.documentElement;
    const p = src?.themeParams ?? {};
    const map: Record<string, string | undefined> = {
      "--tg-theme-bg-color": p.bg_color,
      "--tg-theme-text-color": p.text_color,
      "--tg-theme-hint-color": p.hint_color,
      "--tg-theme-link-color": p.link_color,
      "--tg-theme-button-color": p.button_color,
      "--tg-theme-button-text-color": p.button_text_color,
      "--tg-theme-secondary-bg-color": p.secondary_bg_color,
    };
    Object.entries(map).forEach(([k, v]) => v && root.style.setProperty(k, v));
    if (ignoreScheme) {
      root.classList.remove("dark");
      setScheme("light");
      tg?.setBackgroundColor?.("#ffffff");
      tg?.setHeaderColor?.("#ffffff");
    } else {
      root.classList.toggle("dark", src?.colorScheme === "dark");
      setScheme(src?.colorScheme ?? "light");
    }
  };

  useEffect(() => {
    if (!tg) {
      console.warn("[TG] not in Telegram, enabling dev fallback");
      applyTheme(null, forceLight);
      setReady(true);
      return;
    }
    try {
      tg.expand?.();
      tg.ready?.();
      applyTheme(tg, forceLight);
      setUser(tg.user ?? null);
      setReady(true);
      const onTheme = () => applyTheme(tg, forceLight);
      tg.onEvent?.("themeChanged", onTheme);
      return () => {
        tg.offEvent?.("themeChanged", onTheme);
        if (mainClickRef.current) tg.MainButton?.offClick?.(mainClickRef.current);
        if (backClickRef.current) tg.BackButton?.offClick?.(backClickRef.current);
      };
    } catch (e) {
      console.error("[TG] init error:", e);
      setReady(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tg]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sendData = (data: any) => tg?.sendData?.(JSON.stringify(data));

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

  return { tg, isReady, user, colorScheme, sendData, showMainButton, hideMainButton, showBackButton, hideBackButton };
};
