#!/usr/bin/env bash
# scripts/diag_reminders.sh
set -euo pipefail

# Настройки (можешь менять при запуске через аргументы)
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PROJ_DIR/venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"
DB_NAME="diabetes_bot"
BOT_SERVICE="diabetes-bot.service"
API_SERVICE="diabetes-api.service"

TG_ID="${1:-448794918}"  # можно передать своим первым аргументом
LOG_LINES="${2:-300}"

echo "==[1/8] Время и таймзона сервера ============================"
timedatectl || true
echo
echo "==[2/8] Python-пакеты и версии ==============================="
set +e
"$PY" - <<'PY'
import sys
print("python:", sys.version.replace("\n"," "))
try:
    import telegram
    print("python-telegram-bot:", telegram.__version__)
except Exception as e:
    print("PTB import ERROR:", e)
try:
    import apscheduler
    print("APScheduler:", apscheduler.__version__)
except Exception as e:
    print("APScheduler import ERROR:", e)
try:
    from zoneinfo import ZoneInfo
    print("ZoneInfo('Europe/Moscow') OK")
except Exception as e:
    print("zoneinfo ERROR:", e)
PY
set -e
echo
echo "==[3/8] Проверка systemd unit-файлов ========================="
sudo systemctl cat "$BOT_SERVICE" || true
echo "--------------------------------------------------------------"
sudo systemctl cat "$API_SERVICE" || true
echo
echo "==[4/8] Статус сервисов ======================================"
sudo systemctl status "$BOT_SERVICE" --no-pager || true
echo "--------------------------------------------------------------"
sudo systemctl status "$API_SERVICE" --no-pager || true
echo
echo "==[5/8] Последние логи бота (journalctl) ====================="
sudo journalctl -u "$BOT_SERVICE" -n "$LOG_LINES" --no-pager || true
echo
echo "==[6/8] Поиск ключевых сообщений в логах ====================="
sudo journalctl -u "$BOT_SERVICE" --no-pager | egrep -i \
  "JobQueue|Scheduled job|reminder|apscheduler|timezone|TypeError|ModuleNotFoundError|Traceback" | tail -n 200 || true
echo
echo "==[7/8] Проверка БД: напоминания и логи ======================"
# Подготовим SQL во временный файл
SQL_FILE="$(mktemp)"
cat > "$SQL_FILE" <<SQL
-- >> reminders для TG_ID
SELECT r.id, r.telegram_id, r.enabled, r.time AS reminder_time,
       COALESCE(u.timezone, '(null)') AS user_tz
FROM reminders r
LEFT JOIN users u ON u.telegram_id = r.telegram_id
WHERE r.telegram_id = ${TG_ID}
ORDER BY r.time;

-- >> когда должно было сработать сегодня (MSK)
WITH now_msk AS (
  SELECT (now() AT TIME ZONE 'Europe/Moscow') AS ts
)
SELECT
  r.id,
  r.time AS reminder_time,
  (SELECT ts FROM now_msk) AS now_msk,
  (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time) AS scheduled_today_msk,
  ((SELECT ts FROM now_msk) >= (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time)) AS should_have_fired_today,
  CASE
    WHEN ((SELECT ts FROM now_msk) >= (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time))
      THEN (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time + INTERVAL '1 day')
      ELSE (date_trunc('day',(SELECT ts FROM now_msk))::date + r.time)
  END AS next_run_msk
FROM reminders r
WHERE r.telegram_id = ${TG_ID}
ORDER BY r.time;

-- >> последние события отправки напоминаний
SELECT id, reminder_id, telegram_id,
       sent_at AT TIME ZONE 'Europe/Moscow' AS sent_at_msk,
       status,
       SUBSTRING(COALESCE(error,''),1,200) AS error_short
FROM reminder_logs
WHERE telegram_id = ${TG_ID}
ORDER BY sent_at DESC
LIMIT 25;
SQL
sudo -u postgres psql -d "$DB_NAME" -f "$SQL_FILE" || true
rm -f "$SQL_FILE"
echo
echo "==[8/8] Тест отправки сообщения напрямую ботом (опционально) ="
# Пытаемся прочитать токен из .env и отправить тестовое сообщение.
# Если нет .env или переменной, просто пропустим шаг.
set +e
if [ -f "$PROJ_DIR/.env" ]; then
  while IFS= read -r raw_line; do
    raw_line="${raw_line%$'\r'}"
    trimmed="${raw_line#${raw_line%%[![:space:]]*}}"
    case "$trimmed" in
      ''|\#*) continue ;;
      *=*) ;;
      *) continue ;;
    esac
    key="${trimmed%%=*}"
    value="${trimmed#*=}"
    case "$key" in
      export\ *) key="${key#export }" ;;
    esac
    key="${key%${key##*[![:space:]]}}"
    key="${key#${key%%[![:space:]]*}}"
    if [ -z "$key" ]; then
      continue
    fi
    value="${value#${value%%[![:space:]]*}}"
    value="${value%${value##*[![:space:]]}}"
    if [[ $value == \"*\" ]]; then
      value="${value%\"}"
      value="${value#\"}"
    elif [[ $value == \'*\' ]]; then
      value="${value%\'}"
      value="${value#\'}"
    fi
    value="${value%${value##*[![:space:]]}}"
    value="${value#${value%%[![:space:]]*}}"
    case "$value" in
      \#*) value="" ;;
    esac
    case "$key" in
      BOT_TOKEN|TELEGRAM_BOT_TOKEN)
        export "$key=$value"
        ;;
    esac
  done < "$PROJ_DIR/.env"
fi
BOT_TOKEN="${BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
if [ -n "$BOT_TOKEN" ]; then
  "$PY" - <<PY
import asyncio, os, sys
from datetime import datetime, UTC
try:
    from telegram import Bot
except Exception as e:
    print("PTB import ERROR:", e); sys.exit(0)

token=os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id=int("${TG_ID}")
async def main() -> None:
    bot=Bot(token=token)
    txt=f"Диагностика: бот доступен ✅ (UTC={datetime.now(UTC):%Y-%m-%d %H:%M:%S})"
    await bot.send_message(chat_id=chat_id, text=txt)
asyncio.run(main())
print(">> Сообщение диагностики отправлено (если токен и чат корректны).")
PY
else
  echo "BOT_TOKEN не найден в $PROJ_DIR/.env — шаг пропущен."
fi
set -e
echo
echo "== Готово. Если где-то ERROR — смотри секции [2/8], [4/8], [5/8]. =="
