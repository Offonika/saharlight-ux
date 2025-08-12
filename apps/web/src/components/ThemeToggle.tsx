import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

import { Switch } from "@/components/ui/switch";

/**
 * ThemeToggle toggles between light and dark themes using next-themes.
 */
const ThemeToggle = () => {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const isDark = theme === "dark";

  return (
    <Switch
      checked={isDark}
      onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
      aria-label="Переключить тему"
    />
  );
};

export default ThemeToggle;

