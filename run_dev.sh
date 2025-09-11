#!/usr/bin/env bash
# file: run_dev.sh
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Загружаем переменные окружения
set -a
source ./.env
set +a

# Конфигурация для Matplotlib
export MPLCONFIGDIR="${MPLCONFIGDIR:-$REPO_ROOT/data/mpl-cache}"
mkdir -p "$MPLCONFIGDIR"
chmod 700 "$MPLCONFIGDIR"

# Validate Matplotlib config directory
python - <<'PY'
import os
import sys
import matplotlib

cfg = matplotlib.get_configdir()
expected = os.environ["MPLCONFIGDIR"]
if os.path.realpath(cfg) != os.path.realpath(expected):
    raise SystemExit(f"matplotlib config dir {cfg!r} doesn't match {expected!r}")
if not os.access(cfg, os.W_OK):
    raise SystemExit(f"matplotlib config dir {cfg!r} is not writable")
PY

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
