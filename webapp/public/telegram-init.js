(function () {
    const app = window.Telegram?.WebApp;
    if (!app) {
        return;
    }

    const applyTheme = () => {
        const { bg_color, header_color } = app.themeParams;
        if (bg_color) {
            app.setBackgroundColor(bg_color);
        }
        if (header_color) {
            app.setHeaderColor(header_color);
        }
    };

    app.expand();
    applyTheme();
    app.onEvent('themeChanged', applyTheme);
})();

