#!/usr/bin/env bash
# file: run_dev.sh
set -e

# Загружаем переменные окружения
set -a
source ./.env
set +a

# Конфигурация для Matplotlib
export MPLCONFIGDIR="${MPLCONFIGDIR:-/opt/saharlight-ux/data/mpl-cache}"
mkdir -p "$MPLCONFIGDIR"
chmod 700 "$MPLCONFIGDIR"

# Запускаем API с авто-reload (1 процесс)
uvicorn services.api.app.main:app \
        --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

# Запускаем Telegram-бота
python -m services.bot.main &
BOT_PID=$!

echo "API  PID: $API_PID"
echo "BOT PID: $BOT_PID"
echo "Press Ctrl+C to stop both."

# Корректно завершаем оба при SIGINT/SIGTERM
trap 'kill $API_PID $BOT_PID' INT TERM
wait
