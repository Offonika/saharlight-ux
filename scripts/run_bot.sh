#!/usr/bin/env bash
set -euo pipefail

# Runs the Telegram bot entrypoint.
# Usage: scripts/run_bot.sh [ARGS...]

export PYTHONPATH="$(dirname "$0")/..:$PYTHONPATH"
python -m services.api.app.bot "$@"
