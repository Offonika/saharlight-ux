#!/usr/bin/env bash
set -euo pipefail

# Runs the Telegram bot entrypoint.
# Usage: scripts/run_bot.sh [ARGS...]

REPO_ROOT="$(dirname "${BASH_SOURCE[0]}")/.."
cd "${REPO_ROOT}"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  source .env
  set +a
fi

export MPLCONFIGDIR="${MPLCONFIGDIR:-/opt/saharlight-ux/data/mpl-cache}"
mkdir -p "$MPLCONFIGDIR"
chmod 700 "$MPLCONFIGDIR"

# Validate that Matplotlib uses the configured directory and it's writable
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

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

# basic sanity checks for required configuration
: "${TELEGRAM_TOKEN:?TELEGRAM_TOKEN is not set}"
: "${PUBLIC_ORIGIN:?PUBLIC_ORIGIN is not set}"

# UI_BASE_URL defaults to /ui but can be overridden in the environment
export UI_BASE_URL="${UI_BASE_URL:-/ui}"

exec python -m services.api.app.bot "$@"
