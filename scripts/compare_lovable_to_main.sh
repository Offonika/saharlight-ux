#!/usr/bin/env bash
# file: scripts/compare_lovable_to_main.sh
set -euo pipefail

TARGET=main
SOURCE=lovable
OUTDIR=diagnostics

mkdir -p "$OUTDIR"

echo "== Fetch =="
git fetch --all --prune

compare_pair() {
  local target=$1
  local source=$2
  local label=$3

  echo "== Сравнение $label =="
  git diff --stat origin/$TARGET:$target origin/$SOURCE:$source > $OUTDIR/diffs_${label}.log || true
  git diff origin/$TARGET:$target origin/$SOURCE:$source > $OUTDIR/full_${label}_diff.log || true
}

# src → src
compare_pair "services/webapp/ui/src" "src" "src"

# public → public
compare_pair "services/webapp/ui/public" "public" "public"

# SDK
compare_pair "libs/ts-sdk" "libs/ts-sdk" "sdk"

echo "== Сравнение конфигов =="

# package.json
compare_pair "services/webapp/ui/package.json" "package.json" "package.json"

# vite.config.ts
compare_pair "services/webapp/ui/vite.config.ts" "vite.config.ts" "vite.config.ts"

# tailwind.config (разное расширение)
git diff origin/$TARGET:services/webapp/ui/tailwind.config.ts origin/$SOURCE:tailwind.config.js > $OUTDIR/diff_tailwind_config.log || true

# index.html
compare_pair "services/webapp/ui/index.html" "index.html" "index.html"

# tsconfig.json
compare_pair "services/webapp/ui/tsconfig.json" "tsconfig.json" "tsconfig.json"

# postcss.config.js
compare_pair "services/webapp/ui/postcss.config.js" "postcss.config.js" "postcss.config.js"

echo "== Готово. Результаты сохранены в $OUTDIR =="
ls -lh $OUTDIR
