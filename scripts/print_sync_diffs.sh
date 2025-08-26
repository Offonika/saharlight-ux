#!/usr/bin/env bash
# file: scripts/print_sync_diffs.sh
set -euo pipefail

TARGET_BRANCH="${1:-main}"
SOURCE_BRANCH="${2:-lovable}"

echo "== Fetch =="
git fetch --all --prune

echo "== SHAs =="
SHA_MAIN="$(git rev-parse "origin/${TARGET_BRANCH}")"
SHA_LOV="$(git rev-parse "origin/${SOURCE_BRANCH}")"
echo "HEAD ${TARGET_BRANCH}: ${SHA_MAIN}"
echo "HEAD ${SOURCE_BRANCH}: ${SHA_LOV}"
echo

echo "== Изменённые файлы (только каталоги под автосинк) =="
WHITELIST=(
  "services/webapp/ui/src"
  "services/webapp/ui/public"
  "libs/ts-sdk"
)
for p in "${WHITELIST[@]}"; do
  echo "--- ${p} ---"
  git diff --name-status "origin/${TARGET_BRANCH}..origin/${SOURCE_BRANCH}" -- "${p}" || true
  echo
done

echo "== Краткая статистика по src =="
git diff --shortstat "origin/${TARGET_BRANCH}..origin/${SOURCE_BRANCH}" -- services/webapp/ui/src || true
echo

echo "== Полный список изменений (диагностика) =="
git diff --name-status "origin/${TARGET_BRANCH}..origin/${SOURCE_BRANCH}" || true
echo

echo "== Дельта конфигов (не синкаем автоматически) =="
CONFIGS=(
  "services/webapp/ui/package.json"
  "services/webapp/ui/package-lock.json"
  "services/webapp/ui/vite.config.ts"
  "services/webapp/ui/tailwind.config.ts"
  "services/webapp/ui/postcss.config.js"
  "services/webapp/ui/tsconfig.json"
  "services/webapp/ui/index.html"
)
for f in "${CONFIGS[@]}"; do
  if git diff --name-only "origin/${TARGET_BRANCH}..origin/${SOURCE_BRANCH}" -- "$f" | grep -q .; then
    echo "-- $f"
    git diff --unified=3 "origin/${TARGET_BRANCH}..origin/${SOURCE_BRANCH}" -- "$f" || true
    echo
  fi
done
