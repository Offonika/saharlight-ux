const tg = window.Telegram?.WebApp;
if (tg) {
  try {
    tg.ready();
    const applyTheme = () => {
      tg.setBackgroundColor('#ffffff');
      tg.setHeaderColor('#ffffff');
    };
    applyTheme();
    tg.onEvent('themeChanged', applyTheme);
    tg.BackButton?.hide?.();
    tg.MainButton?.hide?.();
  } catch (e) {
    console.warn('Telegram WebApp init override failed:', e);
  }
}

document.body.classList.add('light-theme');
