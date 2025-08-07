# Dockerfile — контейнеризация Diabetes Bot

FROM python:3.11-slim

WORKDIR /app

EXPOSE 8000

# Установка системных библиотек (PostgreSQL)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Копируйте .env при деплое или используйте секреты Docker Compose!
# COPY .env .env

# Запускаем FastAPI WebApp и Telegram-бота
ENV UVICORN_WORKERS=1
ENV WEBAPP_URL="http://localhost:8000/"
CMD ["bash", "-c", "uvicorn webapp.server:app --host 0.0.0.0 --port 8000 --workers $UVICORN_WORKERS & python bot.py"]
