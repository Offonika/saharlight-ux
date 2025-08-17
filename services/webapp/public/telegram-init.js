(async function () {
    const mod = await import("/assets/telegram-theme.js");
    const applyTheme = mod.applyTheme ?? mod.default ?? mod.a;
    const app = window.Telegram?.WebApp;
    if (!app) {
        return;
    }
    app.expand?.();
    applyTheme(app, true);
    app.onEvent?.('themeChanged', () => applyTheme(app, true));
})();
