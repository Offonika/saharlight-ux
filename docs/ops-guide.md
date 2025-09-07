# Ops Guide

## Health checks

- `GET /api/health` — базовая проверка, сервис отвечает `{"status": "ok"}`.
- `GET /api/health/ping` — быстрый ping базы данных. При успешном подключении возвращает
  `{"status": "up"}`, при недоступности базы отвечает статусом `503` и телом
  `{"status": "down"}`.

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
