# Режим обучения

Режим обучения сохраняет пользовательские запросы и ответы модели для
дальнейшего анализа и дообучения.

В примерах далее используется урок `xe_basics` — базовые хлебные единицы.

## Включение

В файле `.env` установите переменную окружения `LEARNING_MODE_ENABLED` (или
устаревший вариант `LEARNING_ENABLED`) в `true`. Отсутствие или значение
`false` выключает режим обучения.

```bash
LEARNING_MODE_ENABLED=true
```

## Подготовка базы данных

```bash
alembic upgrade head
python -m services.api.app.diabetes.learning_fixtures
```

## Ручная проверка

```bash
python services/api/app/bot.py
python scripts/probe_learn.py --user 123 --lesson xe_basics
```

## Схема базы данных

### lessons
- `id` — первичный ключ
- `slug` — уникальный идентификатор урока
- `title` — название урока
- `content` — текстовое содержание
- `is_active` — признак доступности

### lesson_steps
- `id` — первичный ключ
- `lesson_id` — ссылка на урок
- `step_order` — порядок шага
- `content` — текст шага

### quiz_questions
- `id` — первичный ключ
- `lesson_id` — ссылка на урок
- `question` — формулировка вопроса
- `options` — варианты ответов
- `correct_option` — индекс правильного варианта

### lesson_progress
- `id` — первичный ключ
- `user_id` — Telegram ID пользователя
- `lesson_id` — ссылка на урок
- `completed` — пройден ли урок
- `current_step` — текущий шаг
- `current_question` — текущий вопрос
- `quiz_score` — итоговый балл

## Happy-path для QA

1. В `.env` включить `LEARNING_MODE_ENABLED=true`.
2. Выполнить `alembic upgrade head`.
3. Загрузить данные: `python -m services.api.app.diabetes.learning_fixtures`.
4. Запустить бота `python services/api/app/bot.py` и пройти урок `xe_basics`.
5. Убедиться, что `scripts/probe_learn.py --user 123 --lesson xe_basics`
   возвращает корректные данные.
6. Проверить, что в таблице `lesson_progress` появилась запись с `completed=true`.
