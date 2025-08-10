if (window.Telegram && Telegram.WebApp) {
    const webApp = Telegram.WebApp;
    webApp.ready();
    webApp.expand();

    const applyTheme = () => {
        const { bg_color, header_bg_color } = webApp.themeParams;
        if (bg_color) {
            webApp.setBackgroundColor(bg_color);
        }
        if (header_bg_color) {
            webApp.setHeaderColor(header_bg_color);
        }
    };

    applyTheme();

    webApp.onEvent('themeChanged', applyTheme);
}
