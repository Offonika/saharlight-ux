if (window.Telegram && Telegram.WebApp) {
    const webApp = Telegram.WebApp;
    webApp.ready();
    webApp.expand();

    const applyLightTheme = () => {
        webApp.setBackgroundColor('#ffffff');
        webApp.setHeaderColor('#ffffff');
    };

    if (webApp.colorScheme !== 'light') {
        applyLightTheme();
    }

    webApp.onEvent('themeChanged', () => {
        if (webApp.colorScheme !== 'light') {
            applyLightTheme();
        }
    });
}
