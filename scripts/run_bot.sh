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

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

# basic sanity checks for required configuration
: "${TELEGRAM_TOKEN:?TELEGRAM_TOKEN is not set}"
: "${PUBLIC_ORIGIN:?PUBLIC_ORIGIN is not set}"

# UI_BASE_URL defaults to /ui but can be overridden in the environment
export UI_BASE_URL="${UI_BASE_URL:-/ui}"

exec python -m services.api.app.bot "$@"
