# Ops Guide

## Environment flags

- `API_URL` — базовый URL внешнего API (поддерживается `API_BASE_URL`);
- `INTERNAL_API_KEY` — ключ для внутренней аутентификации бота;
- `SUBSCRIPTION_URL` — страница подписки в WebApp;
- `UI_BASE_URL`/`VITE_API_BASE` — базовые пути фронтенда и API;
- `BILLING_ENABLED`, `BILLING_TEST_MODE`, `BILLING_PROVIDER` — настройки биллинга;
- `LEARNING_MODE_ENABLED` — включает режим обучения;
- `OPENAI_API_KEY`, `OPENAI_ASSISTANT_ID` — ключ и ассистент GPT.

## Migrations

Миграции находятся в `services/api/alembic/` и именуются как
`YYYYMMDD_<описание>.py`.

Применить все миграции:

```bash
make migrate  # или alembic upgrade head
```

Создать новую миграцию:

```bash
alembic revision --autogenerate -m "20250910_add_table"
```

## Health checks

- `GET /api/health` — базовая проверка, сервис отвечает `{"status": "ok"}`.
- `GET /api/health/ping` — быстрый ping базы данных. При успешном подключении
  возвращает `{"status": "up"}`, при недоступности базы отвечает статусом
  `503` и телом `{"status": "down"}`.

## Degradation scenarios

- **База данных недоступна.** Health‑пинг отвечает `503`, метрика
  `db_down_seconds` растёт.
- **Не задан OpenAI API ключ.** Вызовы GPT возвращают сообщение
  `OpenAI API key is not configured`, остальные функции продолжают работать.

## Резервное копирование базы данных

```bash
pg_dump --format=custom \
    --host "$DB_HOST" \
    --username "$DB_USER" \
    "$DB_NAME" > backup.dump
```

Секреты берутся из переменных окружения (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).

## Восстановление базы данных

```bash
pg_restore --clean \
    --host "$DB_HOST" \
    --username "$DB_USER" \
    --dbname "$DB_NAME" \
    backup.dump
```

После восстановления выполните инициализацию БД, чтобы применить права ролей:

```bash
python - <<'PY'
from services.api.app.diabetes.services.db import init_db
init_db()
PY
```

## Testing and metrics

### Tests
```bash
make ci  # pytest --cov, mypy --strict, ruff check
```

### Metrics
```bash
curl http://localhost:8000/api/metrics
curl 'http://localhost:8000/api/metrics/onboarding?from=2025-09-01&to=2025-09-07'
```
