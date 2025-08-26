// file: services/webapp/public/telegram-init.js
(async function () {
  // Абсолютный импорт под базой SPA: /ui/telegram-theme.js
  const { default: applyTheme } = await import(
    new URL('/ui/telegram-theme.js', window.location.origin)
  )

  const app = window.Telegram?.WebApp
  if (!app) return

  app.expand?.()
  applyTheme?.(app, true)
  app.onEvent?.('themeChanged', () => applyTheme?.(app, true))
})()
