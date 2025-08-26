# filename: scripts/print_sync_diffs.sh
#!/usr/bin/env bash
set -euo pipefail

# Настройки
TARGET_BRANCH="${1:-main}"
SOURCE_BRANCH="${2:-lovable}"

echo "== Fetch =="
git fetch --all --prune

echo "== SHAs =="
SHA_MAIN=$(git rev-parse "origin/${TARGET_BRANCH}")
SHA_LOV=$(git rev-parse "origin/${SOURCE_BRANCH}")
echo "HEAD ${TARGET_BRANCH}: ${SHA_MAIN}"
echo "HEAD ${SOURCE_BRANCH}: ${SHA_LOV}"
echo

echo "== Изменённые файлы (только нужные каталоги) =="
# Папки под автосинк
WHITELIST=(
  "services/webapp/ui/src"
  "services/webapp/ui/public"
  "libs/ts-sdk"
)

# Печать списков по каждой папке
for p in "${WHITELIST[@]}"; do
  echo "-- ${p} --"
  git diff --name-status "origin/${TARGET_BRANCH}...origin/${SOURCE_BRANCH}" -- "$p" || true
  echo
done

echo "== Проверка конфигов (если трогались в lovable) =="
CONFIGS=(
  "services/webapp/ui/package.json"
  "services/webapp/ui/vite.config.ts"
  "services/webapp/ui/tailwind.config.ts"
  "services/webapp/ui/index.html"
)

for f in "${CONFIGS[@]}"; do
  # Было ли изменение файла в lovable по сравнению с main?
  if git diff --name-only "origin/${TARGET_BRANCH}...origin/${SOURCE_BRANCH}" -- "$f" | grep -q .; then
    echo "-- DIFF $f --"
    git diff "origin/${TARGET_BRANCH}...origin/${SOURCE_BRANCH}" -- "$f" || true
    echo
  fi
done

echo "== Резюме =="
echo "Если в секции 'Проверка конфигов' пусто — configs не менялись в lovable."
echo "Списки выше показывают, что именно менялось в src/public/libs/ts-sdk."