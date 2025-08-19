(async function () {
    const { default: applyTheme } = await import("./assets/telegram-theme.js");
    const app = window.Telegram?.WebApp;
    if (!app) {
        return;
    }
    app.expand?.();
    applyTheme(app, true);
    app.onEvent?.('themeChanged', () => applyTheme(app, true));
})();
