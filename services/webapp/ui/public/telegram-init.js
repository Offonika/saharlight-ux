(function () {
    const app = window.Telegram?.WebApp;
    if (!app) {
        return;
    }

    const supportsColorMethods = () => {
        const [major = 0, minor = 0] = (app.version || '0.0')
            .split('.')
            .map((n) => parseInt(n, 10));
        if (app.platform === 'tdesktop') {
            return major > 4 || (major === 4 && minor >= 8);
        }
        return major > 6 || (major === 6 && minor >= 1);
    };

    const applyTheme = () => {
        if (supportsColorMethods()) {
            if (app.setBackgroundColor) app.setBackgroundColor('#fff');
            if (app.setHeaderColor) app.setHeaderColor('#fff');
        }
    };

    app.expand?.();
    applyTheme();
    app.onEvent?.('themeChanged', applyTheme);
})();

