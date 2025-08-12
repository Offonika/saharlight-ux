#!/usr/bin/env bash
set -e

if [ ! -d "apps/web/dist" ]; then
    echo "Building web UI..."
    (cd apps/web && npm ci && npm run build)
else
    echo "web UI already built; skipping build"
fi

echo "Starting backend server"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1} &

python apps/telegram_bot/bot.py
