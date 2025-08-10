# Dockerfile — контейнеризация Diabetes Bot

FROM python:3.11-slim

WORKDIR /app

EXPOSE 8000

# Установка системных библиотек (PostgreSQL)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc nodejs npm && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Копируйте .env при деплое или используйте секреты Docker Compose!
# COPY .env .env

# Запуск WebApp теперь контролируется переменной ENABLE_WEBAPP.
# WEBAPP_URL должен указывать на публичный HTTPS-адрес; без него WebApp не стартует.
ENV UVICORN_WORKERS=1
CMD ["bash", "./start.sh"]
