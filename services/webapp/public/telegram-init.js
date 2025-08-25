(async function () {
    const { default: applyTheme } = await import(
        new URL('./telegram-theme.js', import.meta.url),
    );
    const app = window.Telegram?.WebApp;
    if (!app) {
        return;
    }
    app.expand?.();
    applyTheme(app, true);
    app.onEvent?.('themeChanged', () => applyTheme(app, true));
})();
