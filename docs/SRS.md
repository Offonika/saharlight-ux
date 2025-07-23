# Software Requirements Specification

## Telegram-бот
- /start, /photo, /sugar, /dose, /history, /profile, /reset
- Фото еды → ХЕ, доза → запись в БД
- Поддержка голосового ввода

## Серверная часть
- Python + FastAPI, Redis + Celery
- PostgreSQL, Assistant API (GPT-4o)

## SaaS-панель врача
- Лента, отчёты, тревоги, FHIR-экспорт
