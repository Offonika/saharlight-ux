# Руководство по миграциям

## Split Insulin Doses

Документ описывает пошаговый сценарий выката и возможного отката миграции, добавляющей в дневник поля `insulin_short` и `insulin_long`.

### Pre-checks
1. Проверьте состояние репозитория и миграций:
   - `git status` — нет незакоммиченных файлов.
   - `alembic -c services/api/alembic/alembic.ini heads` — только ожидаемая ревизия сплит-доз.
2. Убедитесь, что окружение активировано и зависимости установлены: `pip install -r requirements.txt` и dev-зависимости API.
3. Договоритесь с операторами фоновых воркеров/cron о времени окна — миграция должна выполняться без конкурентных записей.
4. Уточните текущие значения фич-флагов: `kubectl -n diabetes get configmap feature-flags -o yaml | rg insulin_dose_split` — фича должна быть выключена до завершения миграции.
5. Снимите показания мониторинга по метрикам `legacy_dose_used` и `split_dose_saved` (Grafana/Prometheus) для последующего сравнения.

### Backup и подготовка
1. Переведите сервисы, записывающие дневник, в режим read-only: `kubectl -n diabetes scale deploy diary-writer --replicas=0`.
2. Создайте свежий снапшот БД согласно политике окружения, например:
   - `pg_dump --dbname=$DATABASE_URL --format=custom --file=backups/split_doses_before.dump`;
   - либо инициируйте снапшот в Barman: `barman backup prod-diabetes`.
3. Зафиксируйте идентификатор текущей ревизии: `alembic -c services/api/alembic/alembic.ini history --verbose | tail -n 1` и сохраните его в журнале деплоя.

### Порядок действий при апгрейде
1. Подготовьте инфраструктуру:
   - `make migrate` — собирает окружение и применяет все доступные ревизии Alembic;
   - при точечном применении: `alembic -c services/api/alembic/alembic.ini upgrade head`.
2. Выполните прогон автоматизированных smoke-тестов API (минимальный набор):
   - `pytest tests/api/entries/test_split_doses_smoke.py -q`.
3. Запустите сервисы обратно: `kubectl -n diabetes scale deploy diary-writer --replicas=3`.
4. Переключите фич-флаг «split insulin doses» в режим gradual rollout (например, 5 % пользователей) через соответствующий ConfigMap или LaunchDarkly.
5. Мониторьте метрики в течение первого часа. При росте `legacy_dose_used` убедитесь, что клиенты корректно обновлены.

### Smoke-проверки после апгрейда
1. Структура данных:
   - `SELECT column_name FROM information_schema.columns WHERE table_name = 'history_records' AND column_name IN ('insulin_short', 'insulin_long');` — оба столбца должны существовать.
2. CRUD через API:
   - `http POST $API_URL/v1/diary \
       insulin_short:=4.5 insulin_long:=6.0 note='split dose smoke'` — запись должна быть создана;
   - `http GET $API_URL/v1/diary/$ENTRY_ID` — ответ содержит оба поля и поле `dose` становится только для обратной совместимости.
3. Агрегации:
   - `SELECT count(*) FILTER (WHERE insulin_short IS NOT NULL), count(*) FILTER (WHERE insulin_long IS NOT NULL) FROM history_records WHERE created_at >= now() - interval '1 day';` — значения не нулевые.
4. Метрики и логи: убедитесь, что не появляется алёртов в канале observability и что дашборд `Split insulin doses` обновил графики без скачков.

### Трактовка legacy дозы
- Поле `dose` остаётся только для чтения и совместимости. Его значение трактуется как «быстрая» доза (`insulin_short`).
- **Запрещено** копировать значение `dose` одновременно в `insulin_short` и `insulin_long` — это приведёт к удвоению инсулина и нарушит аудит изменений.
- Новые записи должны содержать ровно одну из частей (или обе, если пользователь реально ввёл две разные дозы). При отсутствии длинной дозы поле `insulin_long` остаётся `NULL`.

### План отката
1. Остановите запись новых событий (аналогично pre-checks: `kubectl -n diabetes scale deploy diary-writer --replicas=0`).
2. Отключите фич-флаг «split insulin doses» для всех пользователей.
3. Выполните даунгрейд схемы до сохранённой ревизии:
   - `alembic -c services/api/alembic/alembic.ini downgrade <previous_revision>`.
4. Проверьте, что таблица `history_records` больше не содержит столбцов `insulin_short` и `insulin_long`:
   - `SELECT column_name FROM information_schema.columns WHERE table_name = 'history_records';` — столбцы должны исчезнуть.
5. Восстановите данные из бэкапа при необходимости: `pg_restore --clean --dbname=$DATABASE_URL backups/split_doses_before.dump`.
6. Верните сервисы в online: `kubectl -n diabetes scale deploy diary-writer --replicas=3`.
7. Проведите smoke-проверки legacy API (создание записи без сплит-полей) и убедитесь, что метрика `legacy_dose_used` возвращается к докатному уровню.
8. Создайте запись в журнале инцидентов и запустите постмортем по шаблону DoD.

### Мониторинг и отчётность
- QA следует [тест-плану](qa/split-insulin-doses-testplan.md).
- BI-команда проверяет отчётность согласно [гайду по визуализации](reporting/insulin-doses-rendering.md).
- Через 24 часа убедитесь, что доля событий `legacy_dose_used` остаётся ниже целевого порога, определённого продуктовой аналитикой.
