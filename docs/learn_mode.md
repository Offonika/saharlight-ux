# Режим обучения

Режим обучения сохраняет пользовательские запросы и ответы модели для
дальнейшего анализа и дообучения.

В примерах далее используется урок `xe_basics` — базовые хлебные единицы.

## Включение

В файле `.env` установите переменную окружения `LEARNING_MODE_ENABLED` в `true`.
Переменная `LEARNING_ENABLED` остаётся как устаревший алиас.

```bash
LEARNING_MODE_ENABLED=true
```

## Флаги ассистента

| Флаг | Значение по умолчанию | Описание |
| --- | --- | --- |
| `ASSISTANT_MODE_ENABLED` | `true` | включает режим ассистента |
| `LEARNING_PLANNER_MODEL` | `gpt-4o-mini` | модель построения плана урока |
| `ASSISTANT_MAX_TURNS` | `16` | число сообщений, хранящихся в истории |
| `ASSISTANT_SUMMARY_TRIGGER` | `12` | после стольких сообщений создаётся сводка |
| `LEARNING_PROMPT_CACHE_TTL_SEC` | `28800` | время жизни кэша промптов, сек |

## Подготовка базы данных

```bash
make migrate
```

## Как загрузить уроки

Команду можно запускать сразу после миграции, вручную вызывать `init_db` не
нужно:

```bash
make load-lessons
```

Если фикстуры не загружены — используйте `make seed-l1`.

## Ручная проверка

```bash
python services/api/app/bot.py
python scripts/probe_learn.py --user 123 --lesson xe_basics
```

В Telegram отправьте команду `/learn` и убедитесь, что бот показывает кнопки с уроками.

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
3. Загрузить данные: `make load-lessons`.
4. Проверить содержимое БД: `make db-check`.
5. Запустить бота `python services/api/app/bot.py` и пройти урок `xe_basics`.
6. Убедиться, что `scripts/probe_learn.py --user 123 --lesson xe_basics`
   возвращает корректные данные.
7. Проверить, что в таблице `lesson_progress` появилась запись с `completed=true`.
