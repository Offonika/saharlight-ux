(async function () {
    const themeModules = import.meta?.glob?.("./assets/telegram-theme*.js");
    const mod = themeModules
        ? await themeModules[Object.keys(themeModules)[0]]()
        : await import(new URL("./assets/telegram-theme.js", import.meta.url).href);
    const applyTheme = mod.applyTheme ?? mod.default ?? mod.a;
    const app = window.Telegram?.WebApp;
    if (!app) {
        return;
    }
    app.expand?.();
    applyTheme(app, true);
    app.onEvent?.('themeChanged', () => applyTheme(app, true));
})();
