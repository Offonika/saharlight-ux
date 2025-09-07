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

## Миграции

Перед запуском миграций создайте и активируйте виртуальное окружение:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
make migrate
```

### Установка `diabetes_sdk`
Для доступа к внешнему API нужен приватный пакет `diabetes_sdk`.
Получите доступ у мейнтейнеров и установите его вручную, например:

```bash
# через приватный репозиторий
pip install git+https://github.com/Offonika/diabetes_sdk.git

# либо из локальной сборки SDK
pip install -r libs/py-sdk/requirements.txt
pip install -e libs/py-sdk
```
Если SDK не установлен, функциональность, требующая внешнего API, будет недоступна.

## Запуск API
```bash
uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000
```

## Запуск Бота
```bash
scripts/run_bot.sh
```
Скрипт подгружает `.env` и запускает `services.api.app.bot`.

### Команды BotFather

Зарегистрируйте дополнительные команды в BotFather:

```
/trial - Включить trial
/upgrade - Оформить PRO
```

## Онбординг через WebApp
Первичная настройка пользователя проходит в WebApp. Отдельной страницы
`timezone.html` и кнопки в меню больше нет — бот присылает ссылку на WebApp
после `/start`.

### Пример `/start`
```bash
curl -X POST http://localhost:8000/api/onboarding/events \
  -H 'Content-Type: application/json' \
  -H 'X-Telegram-Init-Data: <init-data>' \
  -d '{"event":"onboarding_started","step":0}'
```

### Пример `/status`
```bash
curl -H 'X-Telegram-Init-Data: <init-data>' \
  http://localhost:8000/api/onboarding/status
```

### Получение `X-Telegram-Init-Data` в WebApp
Внутри Telegram Web App доступ к токену инициализации предоставляет объект
`Telegram.WebApp`. Его значение необходимо передавать в заголовке
`X-Telegram-Init-Data` при обращении к API:

```ts
const tg = window.Telegram.WebApp;
tg.ready();
const initData = tg.initData;

fetch('http://localhost:8000/api/onboarding/status', {
  headers: { 'X-Telegram-Init-Data': initData },
});
```

### События онбординга
- `onboarding_started` — WebApp открыт в режиме онбординга;
- `profile_saved` — профиль сохранён и валиден;
- `first_reminder_created` — создано первое напоминание;
- `onboarding_completed` — финальное событие (если пользователь пропустил
  напоминания, добавляется `skippedReminders: true`).

Онбординг считается завершённым, когда профиль заполнен и есть хотя бы одно
напоминание или получено событие `onboarding_completed` с `skippedReminders`.

## Работа с профилем
После онбординга профиль можно создавать и получать через REST API.

### Создание профиля
```bash
curl -X POST http://localhost:8000/api/profile \
  -H 'Content-Type: application/json' \
  -d '{"telegramId":777,"icr":1.0,"cf":1.0,"target":5.0,"low":4.0,"high":6.0}'
```
Ответ:
```json
{"status": "ok"}
```

### Получение профиля
```bash
curl http://localhost:8000/api/profile?telegramId=777
```

## Переменные окружения
Основные параметры указываются в `.env`:
- `TELEGRAM_TOKEN` — токен бота (обязательно);
- `PUBLIC_ORIGIN` — публичный URL API;
- `WEBAPP_URL` — адрес WebApp для онбординга;
- `API_URL` — базовый URL внешнего API; требует установленный пакет `diabetes_sdk`;
- `OPENAI_API_KEY` — ключ OpenAI для распознавания фото.

Подробнее см. `infra/env/.env.example`.

## Политика хранения данных
Бот сохраняет только идентификаторы пользователей и служебные ссылки на профиль.
Сырые тексты переписки не записываются: таблицы `assistant_memory` и
`lesson_logs` содержат лишь метаданные (счётчики, временные метки, шаги).

## Загрузка уроков
Фикстура `lessons_v0.json` содержит стартовые учебные уроки.
Для загрузки их в базу данных выполните:

```bash
make load-lessons
```

Команда запускает скрипт загрузки и заполняет таблицы обучения.
Перед запуском убедитесь, что база проинициализирована (`make migrate`) и
настроены переменные окружения `DATABASE_URL` либо `DB_HOST`/`DB_PORT`/`DB_NAME`/
`DB_USER`/`DB_PASSWORD`.

### Добавление уроков и регенерация фикстур
1. Добавьте новые записи в `lessons_v0.json`, соблюдая существующий формат.
2. Запустите `make load-lessons`, чтобы записать изменения в базу.
3. При необходимости пересоздайте фикстуру: `python scripts/load_lessons.py --dump lessons_v0.json`.

## Тесты
Установите зависимости и запустите проверки:
```bash
pip install -r services/api/app/requirements-dev.txt
pytest tests/
mypy --strict .
ruff check .
```
