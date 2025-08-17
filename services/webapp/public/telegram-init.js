(async function () {
    const { applyTheme } = await import("/ui/src/lib/telegram-theme.ts");
    const app = window.Telegram?.WebApp;
    if (!app) {
        return;
    }
    app.expand?.();
    applyTheme(app, true);
    app.onEvent?.('themeChanged', () => applyTheme(app, true));
})();
