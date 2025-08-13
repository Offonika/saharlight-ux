(function () {
    const app = window.Telegram?.WebApp;
    if (!app) {
        return;
    }

    const applyTheme = () => {
        app.setBackgroundColor('#fff');
        app.setHeaderColor('#fff');
    };

    app.expand();
    applyTheme();
    app.onEvent('themeChanged', applyTheme);
})();

