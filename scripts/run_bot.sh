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
exec python -m services.api.app.bot "$@"
