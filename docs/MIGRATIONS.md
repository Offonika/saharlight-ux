# Миграция дневника: split insulin doses

Документ описывает практические шаги для выпуска миграции, добавляющей поля `insulin_short` и `insulin_long` в таблицу записей дневника.

## Подготовка
1. Убедитесь, что окружение активировано и установлены зависимости: `pip install -r requirements.txt` и dev-зависимости API.
2. Перед выполнением миграции остановите фоновый воркер, чтобы исключить конкурентные записи.
3. Создайте резервную копию базы (snapshot/Barman/pg_dump — по политике окружения).

## Обновление схемы
1. Запустите стандартный пайплайн: `make migrate` — он собирает окружение и применяет все доступные ревизии Alembic.
2. Если требуется выборочное применение, выполните `alembic -c services/api/alembic/alembic.ini upgrade head`.
3. После апгрейда прогоните дымовые проверки:
   - `SELECT column_name FROM information_schema.columns WHERE table_name = 'history_records' AND column_name IN ('insulin_short','insulin_long');`
   - Через API создать запись с `insulin_short` и убедиться, что в ответе оба поля приходят.
4. **Не выполняйте массовое копирование `dose` → `insulin_short`.** Сервер сам маппит легаси-значения на чтении/записи; дополнительные UPDATE могут испортить аудит изменений.

## План отката
1. Зафиксируйте идентификатор ревизии перед обновлением (см. `alembic history --verbose | tail`).
2. В случае ошибки выполните `alembic -c services/api/alembic/alembic.ini downgrade <previous_revision>`.
3. Верните сервисы в online только после успешного прогона smoke-тестов и проверки телеметрии (см. [metrics](observability/split-insulin-doses-metrics.md)).

## Проверки после деплоя
- QA следует [тест-плану](qa/split-insulin-doses-testplan.md).
- BI-команда проверяет отчётность согласно [гайду по визуализации](reporting/insulin-doses-rendering.md).
- Через 24 часа убедитесь, что доля событий `legacy_dose_used` находится ниже целевого порога.

## Пример SQL для мониторинга
```sql
-- быстрый срез распределения заполненности новых полей
SELECT
  date_trunc('day', created_at) AS day,
  count(*) FILTER (WHERE insulin_short IS NOT NULL) AS short_entries,
  count(*) FILTER (WHERE insulin_long IS NOT NULL) AS long_entries,
  count(*) FILTER (WHERE dose IS NOT NULL AND insulin_short IS NULL) AS legacy_only
FROM history_records
WHERE created_at >= now() - interval '14 days'
GROUP BY 1
ORDER BY 1;
```
