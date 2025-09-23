#!/usr/bin/env bash
# file: run_dev.sh
set -e

DEV_PORT="${DEV_PORT:-8000}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Загружаем переменные окружения
set -a
source ./.env
set +a

# Конфигурация для Matplotlib
export MPLCONFIGDIR="${MPLCONFIGDIR:-${REPO_ROOT}/data/mpl-cache}"
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

# Directory for runtime state
export STATE_DIRECTORY="${STATE_DIRECTORY:-$REPO_ROOT/data/state}"
mkdir -p "$STATE_DIRECTORY"
chmod 700 "$STATE_DIRECTORY"
if [[ ! -w "$STATE_DIRECTORY" ]]; then
  echo "State directory '$STATE_DIRECTORY' is not writable" >&2
  exit 1
fi

# Запускаем API с авто-reload (1 процесс)
if lsof -iTCP:"$DEV_PORT" -sTCP:LISTEN >/dev/null; then
  echo "Port $DEV_PORT is already in use. Set DEV_PORT to use a different port." >&2
  exit 1
fi

uvicorn services.api.app.main:app \
        --reload --host 0.0.0.0 --port "$DEV_PORT" &
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
