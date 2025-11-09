# Документация проекта DiabetAssistent

Эта папка содержит основные документы проекта: цели, требования, архитектуру, безопасность, план тестирования и др.

Фронтенд-зависимости проекта управляются с помощью **pnpm**; команды выполняются из корня репозитория с использованием фильтров.

API требует заголовок `Authorization` с данными инициализации
Telegram WebApp. Унифицированный клиент `httpClient` (через обёртку `api`)
добавляет его автоматически, и запросы без этого заголовка будут отклонены.
Подробности см. в `../README.md` и `SECURITY.md`.

## Структура
- `PRODUCT_PLAN.md` — цели и дорожная карта
- `SRS.md` — функциональные требования
- `Architecture.md` — архитектура и компоненты
- `ADR/` — архитектурные решения (см. новую запись [005 — Split insulin doses](ADR/005-split-insulin-doses.md))
- `adr/2025-11-split-insulin-doses.md` — rationale & scope по разделению болюсных и базальных доз
- `SECURITY.md` — политика безопасности
- `METRICS.md` — метрики продукта и бизнеса
- `QA_Test_Plan.md` — план тестирования
- `MIGRATIONS.md` — практическое руководство по миграции `insulin_short`/`insulin_long`
- `feature-dod/split-insulin-doses.md` — критерии готовности фичи split insulin doses
- `api/entries.md` — временная документация API дневника
- `content/style/` — гайдлайны по копирайтингу (в т.ч. [insulin-doses-copy.md](content/style/insulin-doses-copy.md))
- `reporting/insulin-doses-rendering.md` — правила визуализации доз инсулина
- `qa/split-insulin-doses-testplan.md` — тест-план новой фичи
- `observability/split-insulin-doses-metrics.md` — метрики и алёрты для релиза
- `PERSONAS.md` — пользовательские сегменты
- `learn_mode.md` — описание режима обучения
- `assets/` — медиафайлы для документации и примеров
- `deploy/` — примеры конфигураций для развёртывания, например systemd unit
  `diabetes-bot.service` и `diabetes-assistant.service`

> **Примечание.** API WebApp требует заголовок `Authorization` с данными
> инициализации Telegram. Обёртка `api` добавляет его автоматически;
> запросы без заголовка отклоняются.
