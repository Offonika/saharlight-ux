#!/usr/bin/env bash
# file: scripts/check-sync-readiness.sh
set -euo pipefail

TARGET_BRANCH="${1:-main}"
SOURCE_BRANCH="${2:-lovable}"

git fetch --all --prune > /dev/null

echo "== Проверка guard-путей =="
CHANGED="$(git diff --name-only "origin/${TARGET_BRANCH}..origin/${SOURCE_BRANCH}")"
echo "$CHANGED" | awk '{print " - " $0}'
echo

ALLOWED='^(services/webapp/ui/(src|public)/|libs/ts-sdk/)'
if [ -n "$CHANGED" ] && ! echo "$CHANGED" | grep -Eq "$ALLOWED"; then
  echo "❌ Обнаружены пути вне авто-синка. Нужен отдельный PR."
  exit 1
else
  echo "✅ Все изменения укладываются в guard."
fi

echo
echo "== Локальная сборка UI (сухой прогон) =="
(
  cd services/webapp/ui || { echo "❌ Нет каталога UI"; exit 3; }

  # Чистим старые модули
  rm -rf node_modules

  # Если нет lock — создаём новый
  if [ ! -f package-lock.json ]; then
    echo "⚠️ package-lock.json отсутствует — создаём новый"
    npm install --package-lock-only
  fi

  # Пробуем npm ci → если падает, откатываемся на npm install
  if npm ci --include=dev --no-audit --no-fund --ignore-scripts; then
    echo "✅ npm ci прошёл."
  else
    echo "⚠️ npm ci упал — fallback на npm install..."
    npm install --include=dev --no-audit --no-fund --ignore-scripts
  fi

  # Билдим UI
  if npm run build; then
    echo "✅ Сборка UI прошла."
  else
    echo "❌ Ошибка сборки UI."
    exit 2
  fi
)
