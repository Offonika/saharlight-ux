export type Scheme = "light" | "dark";

export interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

export interface TelegramWebApp {
  version?: string;
  platform?: string;
  themeParams?: ThemeParams;
  colorScheme?: Scheme;
  setBackgroundColor?: (color: string) => void;
  setHeaderColor?: (color: string) => void;
}

export const supportsColorMethods = (app: TelegramWebApp | null): boolean => {
  const [major = 0, minor = 0] = (app?.version || "0.0")
    .split(".")
    .map((n) => parseInt(n, 10));
  if (app?.platform === "tdesktop") {
    return major > 4 || (major === 4 && minor >= 8);
  }
  return major > 6 || (major === 6 && minor >= 1);
};

export function applyTheme(
  src: TelegramWebApp | null,
  ignoreScheme = false,
): Scheme {
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
  if (ignoreScheme) {
    Object.keys(map).forEach((k) => root.style.removeProperty(k));
    root.classList.remove("dark");
    root.style.colorScheme = "light";
    if (src && supportsColorMethods(src)) {
      if (src.setBackgroundColor) src.setBackgroundColor("#ffffff");
      if (src.setHeaderColor) src.setHeaderColor("#ffffff");
    }
    return "light";
  }
  Object.entries(map).forEach(([k, v]) => v && root.style.setProperty(k, v));
  root.style.colorScheme = "";
  const scheme = src?.colorScheme ?? "light";
  root.classList.toggle("dark", scheme === "dark");
  return scheme;
}
