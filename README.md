# Diabetes Bot

## Описание

Телеграм-бот для помощи диабетикам 2 типа:
- 📷 Распознаёт еду по фото через GPT-4o
- 🥗 Считает углеводы и ХЕ
- 💉 (В будущем) Подсказывает дозу инсулина
- 📒 Ведёт дневник питания и сахара

## Структура репозитория

- `services/` — микросервисы и приложения
  - `api/` — FastAPI‑сервер и телеграм‑бот (`services/api/app/diabetes/` — основной пакет с обработчиками)
  - `bot/`, `worker/`, `clinic-panel/` — дополнительные сервисы
  - `webapp/` — React‑SPA (`services/webapp/ui` — исходники, сборка в `dist/`)
- `libs/` — общие библиотеки и SDK
  - `contracts/openapi.yaml` — OpenAPI‑спецификация API
  - `py-sdk/`, `ts-sdk/` — сгенерированные клиентские SDK
- `infra/` — инфраструктура и конфигурации
  - `docker/` — Dockerfile и `docker-compose.yml`
  - `env/.env.example` — пример файла переменных окружения
- `docs/` — проектная документация (см. `docs/README.md`)

Новые обработчики добавляйте в `services/api/app/diabetes/`, создавая отдельные модули с суффиксом `_handlers.py` и группируя их по доменам.

### Доступные команды

- `/start` — запустить бота и показать меню
- `/menu` — открыть главное меню
- `/profile` — мой профиль
- `/report` — отчёт
- `/sugar` — уровень сахара
- `/reminders` — список напоминаний
- `/addreminder` — добавить напоминание
- `/delreminder` — удалить напоминание
- `/cancel` — отменить ввод
- `/help` — справка

### Напоминания

- `/addreminder` запускает мастер создания: выберите тип (сахар, длинный инсулин, лекарство или проверка ХЕ после еды) и укажите время `ЧЧ:ММ`, интервал в часах или минуты после еды. Отменить ввод можно через `/cancel`.
- `/reminders` показывает список напоминаний с их идентификаторами.
- `/delreminder <id>` удаляет напоминание по ID из списка.

Напоминания, созданные через WebApp, сохраняются в базе данных и доступны через API.

---

## Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/Offonika/diabetes-assistant.git
   cd diabetes-assistant
   ```
2. **Создайте виртуальное окружение и активируйте его:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Установите зависимости и соберите фронтенд:**
   ```bash
   pip install -r services/api/app/requirements.txt

   (cd services/webapp/ui && npm ci)

   ```
   Все команды фронтенда (`npm run dev`, `npm run build` и т.д.) запускайте в каталоге `services/webapp/ui`.
4. **Скопируйте шаблон .env и заполните своими данными:**
   ```bash
   cp infra/env/.env.example .env
   # см. раздел "Переменные окружения"
   ```
5. **Инициализируйте базу данных (PostgreSQL):**
   База должна быть уже создана в вашей СУБД, пользователь — иметь права на неё.
   Данные подключения указаны в .env.
   (Если нужен скрипт миграции — опишите отдельно!)


## Переменные окружения

Все секреты и настройки задаются в файле `.env` (см. шаблон `infra/env/.env.example`).

- обязательные значения: `TELEGRAM_TOKEN`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- дополнительные: `LOG_LEVEL` или `DEBUG`, `WEBAPP_URL`, `UVICORN_WORKERS`
- при необходимости настройте прокси для OpenAI через переменные окружения

Telegram‑клиенты не могут обращаться к `localhost`, поэтому `WEBAPP_URL` должен быть публичным **HTTPS**‑адресом. Для локальной разработки используйте туннель (например, [ngrok](https://ngrok.com/)).
Не коммитьте `.env` в репозиторий.

## Запуск

### API
```bash
python services/api/app/main.py
```

### WebApp
Исходники находятся в `services/webapp/ui`.

1. Сборка
   ```bash
   cd services/webapp/ui
   npm run build
   ```
2. Запуск FastAPI
   ```bash
   uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000
   ```

### Docker Compose
```bash
docker compose -f infra/docker/docker-compose.yml up --build
```
API контейнер запускает `uvicorn` напрямую как команду по умолчанию, поэтому отдельный скрипт запуска не требуется.

## Генерация SDK

Файл `libs/contracts/openapi.yaml` содержит спецификацию API. По нему генерируются SDK:

```bash
npx @openapitools/openapi-generator-cli generate -i libs/contracts/openapi.yaml -g python -o libs/py-sdk
npx @openapitools/openapi-generator-cli generate -i libs/contracts/openapi.yaml -g typescript-fetch -o libs/ts-sdk
```

## Сервисный запуск

В каталоге `docs/deploy/` лежат примерные конфигурации для запуска приложения как службы.
Они выполняют `uvicorn services.api.app.main:app --workers 4` и автоматически перезапускаются при сбое.

- `docs/deploy/diabetes-assistant.service` — unit‑файл для **systemd**. Скопируйте его в `/etc/systemd/system/`, отредактируйте пути и пользователя, затем выполните `sudo systemctl enable --now diabetes-assistant`.
- `docs/deploy/supervisord.conf` — секция для **supervisord**. Добавьте её в конфигурацию и перезапустите менеджер процессов.

При необходимости настройте рабочий каталог и параметры запуска под своё окружение.

## Тесты и линтинг

Для проверки качества кода:

```bash
pip install -r services/api/app/requirements-dev.txt
ruff services/api/app/diabetes tests
pytest tests/
```
