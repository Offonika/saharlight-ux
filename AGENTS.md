# AGENTS.md

## 🧑‍💻 Инструкция для Codex и контрибьюторов

Этот проект — телеграм-бот для диабетиков с поддержкой распознавания еды по фото, расчётом ХЕ и дневником.  
В этом файле описано, как агент Codex (и любой разработчик) должен взаимодействовать с репозиторием: запуск, тесты, линтинг, где искать основные файлы и как задавать задачи.

---

## 📐 Правила Codex

- Все функции и методы должны иметь аннотации типов.
- Использование `Any` запрещено; исключения документируйте отдельно.
- Тесты пишите как `def test_*() -> None:`.
- Для предупреждений используйте `warn_or_not` вместо `pytest.warns`.
- Код форматируется Black и проверяется Ruff; строки не длиннее 88 символов.
- Импорты группируются как stdlib, third-party и local, внутри группы сортируются.
- Перед коммитом запускайте `pytest -q && mypy --strict . && ruff check .`.

## 📁 Основные файлы и структура

- **services/api/app/diabetes/** — основной пакет, логика бота
    - **common_handlers.py** — общие обработчики и роутинг
    - **onboarding_handlers.py** — сценарий регистрации и стартовые команды
    - **profile_handlers.py** — управление профилем пользователя
    - **reporting_handlers.py** — дневник питания и отчётность
    - **dose_handlers.py** — расчёт доз инсулина
    - новые модули `*_handlers.py` — для дополнительных сценариев
    - **db.py, models.py** — работа с БД
    - **functions.py** — расчёты и парсинг
    - **gpt_client.py** — работа с OpenAI
- **services/api/app/requirements.txt** — зависимости Python
- **setup.sh** — автоматическая установка окружения
- **infra/docker/Dockerfile.api** — для контейнеризации и Codex
- **infra/docker/docker-compose.yml** — пример конфигурации Docker Compose
- **infra/env/.env.example** — шаблон для переменных окружения
- **tests/** — директория для автотестов (по мере развития)
  
Все обработчики располагаются в отдельных файлах с суффиксом `_handlers.py` в каталоге `services/api/app/diabetes/`. Добавляя новый функционал, создавайте новый модуль или дополняйте существующий, придерживаясь тематического разделения.

---

## 🚀 Запуск локально или в Codex

1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/Offonika/saharlight-ux.git
    cd saharlight-ux
    ```
2. Выполните установку зависимостей и настройте окружение:
    ```bash
    bash setup.sh
    cp infra/env/.env.example .env
    # Впишите свои значения в .env
    source venv/bin/activate
    python services/api/app/bot.py
    ```

3. Для Docker/Codex:
    ```bash
    docker build -t diabetes-bot .
    docker run --env-file .env diabetes-bot
    ```

---

## 🧪 Тесты и качество кода

- **Тесты**: (добавляйте в папку `tests/`, по мере развития)
    ```bash
    pip install pytest
    pytest tests/
    ```
- **Линтинг**: PEP8-стиль
    ```bash
    pip install -r services/api/app/requirements-dev.txt
    ruff services/api/app tests
    ```

---

## 🛠️ Переменные окружения и секреты

- Все чувствительные данные (токены, ключи) НЕ коммитятся, а задаются через `.env` или секреты Codex.
- Пример файла смотрите в `infra/env/.env.example`

---

## ⚡ Примеры задач для Codex/разработки

- **Рефакторинг:**
  _Refactor services/api/app/diabetes/handlers.py, split into smaller modules for readability and maintainability. Add type hints and docstrings._
- **Покрытие тестами:**
  _Add pytest unit tests for services/api/app/diabetes/functions.py, cover all calculation logic._
- **CI и линтинг:**
  _Run ruff on services/api/app/ and tests/, fix all style issues. Add a pre-commit hook if needed._
- **Документация:**
  _Generate and update code documentation. Add docstrings to all public functions._
- **Безопасность:**
  _Audit services/api/app/diabetes/db.py for ORM or SQL security issues. Implement parameterized queries if needed._
- **Docker:**  
  _Check that infra/docker/Dockerfile.api builds and runs with .env, update README.md with Docker instructions._

---

## 📝 Дополнительно

- Если нужно добавить команды для тестирования, линтинга или деплоя — пропишите здесь или в README.md.
- При отправке PR следуйте структуре: `[module] <описание>`, например `[handlers] Add type hints to handlers.py`

---

**Если у вас есть вопросы по архитектуре, структуре кода или интеграции — спрашивайте Codex через режим "Ask", либо создавайте задачи через Issues или Pull Requests.**

---

