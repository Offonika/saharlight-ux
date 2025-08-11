#!/usr/bin/env bash
set -e

if [ ! -d "webapp/ui/dist" ]; then
    echo "Building webapp UI..."
    (cd webapp/ui && npm ci && npm run build)
else
    echo "webapp UI already built; skipping build"
fi

echo "Starting backend server"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1} &

python backend/bot.py
