# Diabetes Bot

## Описание
Телеграм-бот для помощи диабетикам 2 типа:
- распознаёт еду по фото через GPT-4o
- рассчитывает углеводы и ХЕ
- (в будущем) подсказывает дозу инсулина
- ведёт простой дневник

## Установка

1. Клонировать репозиторий:
   ```bash
   git clone <repo_url>
   cd diabetes_bot
   ```
2. Скопируйте файл `.env.example` в `.env` и заполните значения переменных.

### Переменные окружения

- `TELEGRAM_TOKEN` – токен вашего Telegram-бота
- `OPENAI_API_KEY` – ключ API OpenAI
- `OPENAI_ASSISTANT_ID` – ID ассистента OpenAI
- `OPENAI_PROXY` – опциональный прокси для запросов к OpenAI
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` – настройки базы данных
