# Diabetes Bot

## Описание

Телеграм-бот для помощи диабетикам 2 типа:
- 📷 Распознаёт еду по фото через GPT-4o
- 🥗 Считает углеводы и ХЕ
- 💉 (В будущем) Подсказывает дозу инсулина
- 📒 Ведёт дневник питания и сахара

### Структура

- `services/api/app/diabetes/` — основной пакет
  - `common_handlers.py` — общие обработчики и роутинг
  - `onboarding_handlers.py` — регистрация и стартовые команды
  - `profile_handlers.py` — профиль пользователя
  - `reporting_handlers.py` — дневник и отчётность
  - `dose_handlers.py` — расчёт доз инсулина
  - новые файлы `*_handlers.py` — для прочих сценариев
- `services/api/app/main.py` — FastAPI‑приложение: отдаёт WebApp и REST API
- `services/webapp/ui` — исходники фронтенда (React + Vite, собирается в `dist/`)

Новые обработчики добавляйте в каталог `services/api/app/diabetes/`, создавая отдельные модули с суффиксом `_handlers.py` и группируя их по доменам.

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

    (cd services/webapp/ui && npm ci && npm run build)

    ```
    Все команды фронтенда (`npm run dev`, `npm run build` и т.д.) запускайте в каталоге `services/webapp/ui`.
4. **Скопируйте шаблон .env и заполните своими данными:**
   ```bash
   cp infra/env/.env.example .env
   # Откройте .env и впишите свои ключи (Telegram, OpenAI, БД)
   ```
    Обязательно укажите значение переменной `TELEGRAM_TOKEN` — без неё бот не запустится. Также задайте `DB_PASSWORD`; при его отсутствии модуль конфигурации завершится с исключением. Для подробных логов задайте `LOG_LEVEL=DEBUG` (или `DEBUG=1`).
    Чтобы использовать WebApp, укажите `WEBAPP_URL`. Telegram‑клиенты не могут обращаться к `localhost`, поэтому страница должна быть доступна по публичному **HTTPS**‑адресу, например `https://your-domain.example/`. Для локальной разработки используйте туннель (см. ниже).
5. **Инициализируйте базу данных (PostgreSQL):**
   База должна быть уже создана в вашей СУБД, пользователь — иметь права на неё.
   Данные подключения указаны в .env.
   (Если нужен скрипт миграции — опишите отдельно!)

6. **Запустите сервисы:**
   - **API:**
     ```bash
     uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000
     ```
   - **Bot:**
     ```bash
     python services/api/app/bot.py
     ```
   - **WebApp (dev):**
     ```bash
     cd services/webapp/ui
     npm run dev
     ```

### Запуск WebApp

В каталоге `services/webapp/ui` расположен React‑SPA (Vite), исходники лежат в `src/`,
а результат сборки — в `dist/`. Все команды `npm` запускаются из этого каталога.
Файл `services/api/app/main.py` отдаёт содержимое
каталога `services/webapp/ui/dist` и предоставляет REST API (`/api/timezone`,
`/api/profile`, `/api/reminders`).

1. **Сборка интерфейса**

   В CI и скриптах деплоя автоматически выполняется:

   ```bash
    npm run build
   ```

   Ручная сборка нужна только для локального тестирования изменений:

   ```bash
     cd services/webapp/ui
    npm ci
    npm run build
   ```

2. **Запустите FastAPI‑приложение:**
   ```bash
    uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000
   ```
   Количество воркеров можно настроить переменной окружения `UVICORN_WORKERS`.

SPA будет доступна по адресу `/ui` и автоматически отправит часовой пояс на endpoint `POST /api/timezone` в формате `{"tz": "Europe/Moscow"}`. В ответ сервер возвращает `{ "status": "ok" }` и сохраняет значение в базе данных.
Любые маршруты внутри `/ui/*` обслуживаются через fallback на `index.html`,
поэтому прямые переходы по ссылкам не приводят к ошибке 404.
Также сервер раздаёт статические файлы из каталога `services/webapp/public` напрямую, поэтому страницы и ассеты доступны по прямым путям вроде `/timezone.html` или `/telegram-init.js`.

Переменная `WEBAPP_URL` должна указывать на публичный HTTPS‑адрес, по которому SPA доступна пользователю. В Docker‑образе WebApp запускается автоматически; для корректной работы укажите валидный `WEBAPP_URL`.

Чтобы Telegram смог загрузить страницу с вашего локального компьютера, её нужно сделать доступной из интернета. Простой способ — поднять HTTPS‑туннель к локальному порту с помощью [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
```

Скопируйте выданный `https://`‑URL в переменную `WEBAPP_URL`. Аналогичную задачу решают и другие сервисы (Cloudflare Tunnel, localtunnel и т.д.).


**Дополнительно**
- **Docker:** Для контейнеризации можно использовать infra/docker/Dockerfile.api и infra/docker/docker-compose.yml.
- **Proxy:** Для обхода блокировок OpenAI используйте настройки прокси в .env.
- **Безопасность:** Никогда не выкладывайте файл .env с реальными токенами!

## Генерация SDK

Спецификация API находится в `libs/contracts/openapi.yaml`. Для обновления SDK выполните:

```bash
npm install @openapitools/openapi-generator-cli

# TypeScript SDK
npx openapi-generator-cli generate \
  -i libs/contracts/openapi.yaml \
  -g typescript-fetch \
  -o libs/ts-sdk

# Python SDK
npx openapi-generator-cli generate \
  -i libs/contracts/openapi.yaml \
  -g python \
  -o libs/py-sdk \
  -p packageName=diabetes_sdk
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
