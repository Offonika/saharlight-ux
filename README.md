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

3. Установите зависимости из файла `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```
4. Запустите миграции базы данных:
   ```bash
   alembic upgrade head
   ```

## Запуск

- Телеграм-бот:
  ```bash
  python bot.py
  ```
- REST API:
  ```bash
  uvicorn api:app --reload
  ```

## Примеры использования

После запуска бота отправьте фото еды в личный чат – бот вернёт карточку с
подсчётом углеводов и кнопку «Протокол». Подробнее см. сценарии из
[tests/manual_test_cases.md](tests/manual_test_cases.md).

## Тестирование и линтинг

1. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install pytest
   ```
2. Запустите проверки:
   ```bash
   flake8
   pytest
   ```
