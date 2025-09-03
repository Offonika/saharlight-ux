# Onboarding video script

1. **Скачиваем репозиторий и устанавливаем зависимости**
   ```bash
   git clone https://github.com/Offonika/saharlight-ux.git
   cd saharlight-ux
   bash setup.sh
   cp infra/env/.env.example .env
   ```
   Заполните `.env` токеном бота, `PUBLIC_ORIGIN` и ключом OpenAI.

2. **Запускаем API**
   ```bash
   uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000
   ```

3. **В новом терминале стартуем бота**
   ```bash
   scripts/run_bot.sh
   ```

4. **Добавляем WebApp‑кнопку в меню**
   ```bash
   curl -X POST https://api.telegram.org/bot${TELEGRAM_TOKEN}/setChatMenuButton \
     -d '{"menu_button":{"type":"web_app","text":"Open WebApp","web_app":{"url":"'"${WEBAPP_URL}"'"}}}'
   ```

5. **Открываем Telegram и отправляем `/start`. Готово!**
