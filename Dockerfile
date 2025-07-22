# Dockerfile — контейнеризация Diabetes Bot

FROM python:3.11-slim

WORKDIR /app

# Установка системных библиотек (PostgreSQL)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Копируйте .env при деплое или используйте секреты Docker Compose!
# COPY .env .env

CMD ["python", "bot.py"]
