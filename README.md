# Diabetes Bot

## Описание
Телеграм-бот для помощи диабетикам 2 типа:
- 📷 Распознаёт еду по фото через GPT-4o
- 🥗 Считает углеводы и ХЕ
- 💉 (в будущем) Подсказывает дозу инсулина
- 📒 Ведёт дневник питания и сахара

История событий сохраняется в PostgreSQL (таблица `history_records`). Миграции лежат в `services/api/alembic/`.

## Структура репозитория
- `services/` — микросервисы и приложения
  - `api/` — FastAPI‑сервер и телеграм‑бот (`services/api/app/diabetes/` — основной пакет)
  - `bot/`, `worker/`, `clinic-panel/` — дополнительные сервисы
  - `webapp/` — React‑SPA (`services/webapp/ui` — исходники, сборка в `services/webapp/ui/dist/`)
- `libs/` — библиотеки и SDK
- `infra/` — инфраструктура и конфигурации (`infra/env/.env.example` — пример переменных)
- `docs/` — документация (см. `docs/README.md`)

## Установка
```bash
git clone https://github.com/Offonika/saharlight-ux.git
cd saharlight-ux
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r services/api/app/requirements-dev.txt
corepack enable || npm install -g pnpm
pnpm install
pnpm --filter services/webapp/ui run build
cp infra/env/.env.example .env
```
Заполните `.env` своими значениями.

## Запуск API
```bash
uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000
```

## Запуск Бота
```bash
scripts/run_bot.sh
```
Скрипт подгружает `.env` и запускает `services.api.app.bot`.

## Настройка WebApp-кнопки в меню
После деплоя WebApp укажите его адрес в `WEBAPP_URL` и выполните:
```bash
curl -X POST https://api.telegram.org/bot${TELEGRAM_TOKEN}/setChatMenuButton \
  -d '{"menu_button":{"type":"web_app","text":"Open WebApp","web_app":{"url":"'"${WEBAPP_URL}"'"}}}'
```
Вернуть стандартное меню:
```bash
curl -X POST https://api.telegram.org/bot${TELEGRAM_TOKEN}/setChatMenuButton \
  -d '{"menu_button":{"type":"default"}}'
```

## Переменные окружения
Основные параметры указываются в `.env`:
- `TELEGRAM_TOKEN` — токен бота (обязательно);
- `PUBLIC_ORIGIN` — публичный URL API;
- `WEBAPP_URL` — адрес WebApp для кнопки (опционально);
- `API_URL` — базовый URL внешнего API; требует установленный пакет `diabetes_sdk`;
- `OPENAI_API_KEY` — ключ OpenAI для распознавания фото.

Подробнее см. `infra/env/.env.example`.

## Тесты
Установите зависимости и запустите проверки:
```bash
pip install -r services/api/app/requirements-dev.txt
pytest tests/
mypy --strict .
ruff check .
```
