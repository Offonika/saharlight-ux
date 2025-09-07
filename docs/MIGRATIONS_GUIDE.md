# 📜 MIGRATIONS_GUIDE.md

Руководство по работе с миграциями Alembic для проекта **saharlight-ux**.  
Этот документ обязателен к соблюдению как агентом Codex, так и любым контрибьютором.

---

## 🗂️ Основные правила

- Все изменения схемы БД вносятся только через **Alembic**.
- Название файла миграции строгое:  
  `YYYYMMDD_<описание>.py`  
  (где `YYYYMMDD` — дата по UTC, `<описание>` — короткое название snake_case).
- Внутри файла:
  - `revision` = имя файла (идентификатор).
  - `down_revision` = предыдущая миграция или merge-head.
- Все операции должны соответствовать изменениям в моделях (`models.py`).
- В PR с миграциями обязательно прикладывать описание изменений схемы.

---

## 🚀 Создание новой миграции

1. Убедитесь, что локальная база в актуальном состоянии:
   ```bash
   make migrate
Создайте ревизию:

bash
Copy code
alembic revision -m "описание изменений"
Отредактируйте файл:

Проверьте правильность revision и down_revision.

Внесите изменения через op.add_column, op.drop_column, op.create_foreign_key и т.п.

Для ENUM или сложных случаев используйте op.execute.

Примените миграцию:

bash
Copy code
make migrate
Убедитесь, что тесты и линтер проходят:

bash
Copy code
pytest
mypy --strict
ruff check .
🔀 Merge heads
Иногда Alembic сообщает о нескольких «головах» (multiple heads).
В этом случае нужно создать merge-миграцию:

bash
Copy code
alembic revision -m "merge heads" --head <head1> --head <head2>
В таких миграциях не пишем SQL, только связываем историю.

Файл должен содержать revision, down_revision (кортеж из heads).

🎭 Работа с ENUM
ENUM в PostgreSQL — частый источник ошибок. Чтобы избежать «DuplicateObject»:

Никогда не пишите CREATE TYPE напрямую в миграциях.

Для изменения ENUM используйте postgresql.ENUM и op.alter_column.

Пример добавления нового значения в subscription_plan:

python
Copy code
from sqlalchemy.dialects import postgresql

old_type = postgresql.ENUM('free', 'pro', name='subscription_plan')
new_type = postgresql.ENUM('free', 'pro', 'family', name='subscription_plan')

op.alter_column(
    'users',
    'plan',
    type_=new_type,
    existing_type=old_type,
    nullable=False,
    server_default='free',
)
🧹 Foreign Keys и индексы
Перед добавлением нового FK всегда проверяйте, не существует ли он уже:

sql
Copy code
\d+ table_name
Если нужно изменить поведение (ON DELETE CASCADE):

Удалите старое ограничение (op.drop_constraint).

Добавьте новое (op.create_foreign_key).

Пример:

python
Copy code
op.drop_constraint("lesson_logs_user_id_fkey", "lesson_logs", type_="foreignkey")
op.create_foreign_key(
    "lesson_logs_user_id_fkey",
    "lesson_logs",
    "users",
    ["user_id"],
    ["telegram_id"],
    ondelete="CASCADE",
)
🐛 Отладка и ошибки
Проверить текущую версию
bash
Copy code
psql -d diabetes_bot -c "SELECT * FROM alembic_version;"
Откатить последнюю миграцию
bash
Copy code
alembic downgrade -1
Применить заново
bash
Copy code
alembic upgrade head
Полный сброс БД (если миграции не починить)
bash
Copy code
dropdb diabetes_bot && createdb diabetes_bot
make migrate
⚙️ Codex и CI
Каждый PR с миграциями должен:

успешно проходить:

bash
Copy code
make migrate
на чистой базе,

содержать только актуальные изменения (alembic revision --autogenerate использовать осторожно),

включать тесты, если добавлены новые таблицы/колонки.

CI прогоняет:

bash
Copy code
pytest
mypy --strict
ruff check .
make migrate
✅ Чеклист перед PR
 Имя файла соответствует шаблону.

 revision совпадает с именем файла.

 down_revision корректный.

 Нет дубликатов ENUM и FK.

 make migrate успешно на чистой БД.

 Все тесты и линтер прошли.













