# AGENTS.md

## 🧑‍💻 Инструкция для Codex и контрибьюторов

Этот проект — телеграм-бот для диабетиков с поддержкой распознавания еды по фото, расчётом ХЕ и дневником.  
В этом файле описано, как агент Codex (и любой разработчик) должен взаимодействовать с репозиторием: запуск, тесты, линтинг, где искать основные файлы и как задавать задачи.

---

## 📁 Основные файлы и структура

- **backend/diabetes/** — основной пакет, логика бота
    - **common_handlers.py** — общие обработчики и роутинг
    - **onboarding_handlers.py** — сценарий регистрации и стартовые команды
    - **profile_handlers.py** — управление профилем пользователя
    - **reporting_handlers.py** — дневник питания и отчётность
    - **dose_handlers.py** — расчёт доз инсулина
    - новые модули `*_handlers.py` — для дополнительных сценариев
    - **db.py, models.py** — работа с БД
    - **functions.py** — расчёты и парсинг
    - **gpt_client.py** — работа с OpenAI
- **backend/requirements.txt** — зависимости Python
- **setup.sh** — автоматическая установка окружения
- **Dockerfile** — для контейнеризации и Codex
- **backend/.env.example** — шаблон для переменных окружения
- **tests/** — директория для автотестов (по мере развития)
  
Все обработчики располагаются в отдельных файлах с суффиксом `_handlers.py` в каталоге `backend/diabetes/`. Добавляя новый функционал, создавайте новый модуль или дополняйте существующий, придерживаясь тематического разделения.

---

## 🚀 Запуск локально или в Codex

1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/Offonika/diabetes-assistant.git
    cd diabetes-assistant
    ```
2. Выполните установку зависимостей и настройте окружение:
    ```bash
    bash setup.sh
    cp backend/.env.example .env
    # Впишите свои значения в .env
    source venv/bin/activate
    python backend/bot.py
    ```

3. Для Docker/Codex:
    ```bash
    docker build -t diabetes-bot .
    docker run --env-file .env diabetes-bot
    ```

---

## 🧪 Тесты и качество кода

- **Тесты**: (добавляйте в папку `apps/telegram-bot/tests/`, по мере развития)
    ```bash
    pip install pytest
    pytest apps/telegram-bot/tests/
    ```
- **Линтинг**: PEP8-стиль
    ```bash
    pip install -r backend/requirements-dev.txt
    ruff backend/diabetes apps/telegram-bot/tests
    ```

---

## 🛠️ Переменные окружения и секреты

- Все чувствительные данные (токены, ключи) НЕ коммитятся, а задаются через `.env` или секреты Codex.
- Пример файла смотрите в `backend/.env.example`

---

## ⚡ Примеры задач для Codex/разработки

- **Рефакторинг:**
  _Refactor backend/diabetes/handlers.py, split into smaller modules for readability and maintainability. Add type hints and docstrings._
- **Покрытие тестами:**
  _Add pytest unit tests for backend/diabetes/functions.py, cover all calculation logic._
- **CI и линтинг:**
  _Run ruff on backend/diabetes/ and tests/, fix all style issues. Add a pre-commit hook if needed._
- **Документация:**
  _Generate and update code documentation. Add docstrings to all public functions._
- **Безопасность:**
  _Audit backend/diabetes/db.py for ORM or SQL security issues. Implement parameterized queries if needed._
- **Docker:**  
  _Check that Dockerfile builds and runs with .env, update README.md with Docker instructions._

---

## 📝 Дополнительно

- Если нужно добавить команды для тестирования, линтинга или деплоя — пропишите здесь или в README.md.
- При отправке PR следуйте структуре: `[module] <описание>`, например `[handlers] Add type hints to handlers.py`

---

**Если у вас есть вопросы по архитектуре, структуре кода или интеграции — спрашивайте Codex через режим "Ask", либо создавайте задачи через Issues или Pull Requests.**

---

