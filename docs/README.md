# Документация проекта DiabetAssistent

Эта папка содержит основные документы проекта: цели, требования, архитектуру, безопасность, план тестирования и др.

Фронтенд-зависимости проекта управляются с помощью **pnpm**; команды выполняются из корня репозитория с использованием фильтров.

API требует заголовок `Authorization` с данными инициализации
Telegram WebApp. Унифицированный клиент `httpClient` (через обёртку `api`)
добавляет его автоматически, и запросы без этого заголовка будут отклонены.
Подробности см. в `../README.md` и `SECURITY.md`.

## Оглавление

- [Стратегия и продукт](#стратегия-и-продукт)
- [Функциональные требования и фичи](#функциональные-требования-и-фичи)
- [Архитектура, миграции и API](#архитектура-миграции-и-api)
- [Обучение и ассистент](#обучение-и-ассистент)
- [UX, контент и онбординг](#ux-контент-и-онбординг)
- [Отчётность и аналитика](#отчётность-и-аналитика)
- [Наблюдаемость и метрики](#наблюдаемость-и-метрики)
- [Качество и тестирование](#качество-и-тестирование)
- [Операции и релизы](#операции-и-релизы)
- [Безопасность](#безопасность)
- [Ресурсы и ассеты](#ресурсы-и-ассеты)

## Стратегия и продукт

- [BRD.md](BRD.md) — описание продукта и бизнес-контекста.
- [PRODUCT_PLAN.md](PRODUCT_PLAN.md) — цели и дорожная карта.
- [Концепция проекта](Концепция_проекта.md) — позиционирование и сценарии.
- [PERSONAS.md](PERSONAS.md) — ключевые пользовательские сегменты.
- [UI_KIT.md](UI_KIT.md) — дизайн-система и гайдлайны компонентов.
- [release_plan.md](release_plan.md) — план релиза и ключевые вехи.

## Функциональные требования и фичи

- [SRS.md](SRS.md) — системные требования и сценарии.
- [feature_my_profile.md](feature_my_profile.md) — спецификация раздела «Мой профиль».
- [feature-dod/](feature-dod/) — чек-листы готовности фич (см. [split-insulin-doses](feature-dod/split-insulin-doses.md)).
- [tasks/freeform_gpt_chat.md](tasks/freeform_gpt_chat.md) — backlog задач по свободному GPT-диалогу.
- [telegram-compat.md](telegram-compat.md) — совместимость Telegram-клиентов.

## Архитектура, миграции и API

- [Architecture.md](Architecture.md) — обзор системы и компонентов.
- [ADR/](ADR/) — принятые решения, включая [005 — Split insulin doses](ADR/005-split-insulin-doses.md).
- [adr/2025-11-split-insulin-doses.md](adr/2025-11-split-insulin-doses.md) — rationale и область внедрения split-doses.
- [MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md) — правила и примеры миграций.
- [MIGRATIONS.md](MIGRATIONS.md) — практическое руководство по миграции `insulin_short`/`insulin_long` и связанным шагам.
- [api/entries.md](api/entries.md) — спецификация полей дневника.

## Обучение и ассистент

- [learn_mode.md](learn_mode.md) — базовый режим обучения.
- [learn_mode_dynamic.md](learn_mode_dynamic.md) — динамический режим обучения и управление шагами.
- [onboarding_webapp_flow.md](onboarding_webapp_flow.md) — сценарий онбординга в WebApp.
- [onboarding_video_script.md](onboarding_video_script.md) — сценарий видео-онбординга.

## UX, контент и онбординг

- [content/style/insulin-doses-copy.md](content/style/insulin-doses-copy.md) — копирайтинг для раздельных доз.
- [ux/](ux/) — схемы UX и соответствие напоминаний (см. [reminders-insulin-mapping](ux/reminders-insulin-mapping.md)).

## Отчётность и аналитика

- [reporting/insulin-doses-rendering.md](reporting/insulin-doses-rendering.md) — визуализация доз инсулина в отчётах.
- [METRICS.md](METRICS.md) — продуктовые и бизнес-метрики.

## Наблюдаемость и метрики

- [observability/split-insulin-doses-metrics.md](observability/split-insulin-doses-metrics.md) — телеметрия релиза split insulin doses.
- [ALERTS.md](ALERTS.md) — алёрты и реакции на инциденты.

## Качество и тестирование

- [QA_Test_Plan.md](QA_Test_Plan.md) — общий план тестирования.
- [QA_Subscription_Checklist.md](QA_Subscription_Checklist.md) — чек-лист подписочного сценария.
- [qa/split-insulin-doses-testplan.md](qa/split-insulin-doses-testplan.md) — тест-план релиза split insulin doses.

## Операции и релизы

- [ops-guide.md](ops-guide.md) — эксплуатация и операционные процессы.
- [deploy/](deploy/) — конфигурации и примеры деплоя (systemd units и др.).
- [infra/](../infra/) — Docker и инфраструктурные настройки проекта.

## Безопасность

- [SECURITY.md](SECURITY.md) — политика безопасности и требования к API.

## Ресурсы и ассеты

- [assets/](assets/) — изображения и вспомогательные файлы.
- [index.html](index.html) — статический индекс для быстрой навигации.

> **Примечание.** API WebApp требует заголовок `Authorization` с данными
> инициализации Telegram. Обёртка `api` добавляет его автоматически;
> запросы без заголовка отклоняются.
