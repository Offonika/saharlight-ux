#!/usr/bin/env bash
set -e

if [ "$ENABLE_WEBAPP" = "1" ] || [ "$ENABLE_WEBAPP" = "true" ]; then
    if [ -n "$WEBAPP_URL" ] && [[ "$WEBAPP_URL" == https://* ]]; then
        if [ ! -d "apps/web/dist" ]; then
            echo "Building webapp UI..."
            (cd apps/web && npm ci && npm run build)
        else
            echo "webapp UI already built; skipping build"
        fi
        echo "Starting WebApp at $WEBAPP_URL"
        uvicorn webapp.server:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1} &
    else
        echo "ENABLE_WEBAPP is set but WEBAPP_URL is missing or not HTTPS; WebApp will not start."
    fi
else
    echo "ENABLE_WEBAPP not set; WebApp will not start."
fi

python backend/bot.py
