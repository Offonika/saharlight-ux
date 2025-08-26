#!/usr/bin/env bash
# file: scripts/compare_lovable_to_main.sh
set -euo pipefail

TARGET=main
SOURCE=lovable
OUTDIR=diagnostics

mkdir -p "$OUTDIR"

echo "== Fetch =="
git fetch --all --prune

echo "== Сравнение src =="
git diff --stat origin/$TARGET:services/webapp/ui/src origin/$SOURCE:src > $OUTDIR/diffs_src.log
git diff origin/$TARGET:services/webapp/ui/src origin/$SOURCE:src > $OUTDIR/full_src_diff.log || true

echo "== Сравнение public =="
git diff --stat origin/$TARGET:services/webapp/ui/public origin/$SOURCE:public > $OUTDIR/diffs_public.log
git diff origin/$TARGET:services/webapp/ui/public origin/$SOURCE:public > $OUTDIR/full_public_diff.log || true

echo "== Сравнение SDK =="
git diff --stat origin/$TARGET:libs/ts-sdk origin/$SOURCE:libs/ts-sdk > $OUTDIR/diffs_sdk.log
git diff origin/$TARGET:libs/ts-sdk origin/$SOURCE:libs/ts-sdk > $OUTDIR/full_sdk_diff.log || true

echo "== Сравнение конфигов =="
FILES=(package.json vite.config.ts tailwind.config.ts index.html tsconfig.json)
for f in "${FILES[@]}"; do
  if git ls-tree -r origin/$SOURCE --name-only | grep -q "^$f$"; then
    echo "-- $f"
    git diff origin/$TARGET:services/webapp/ui/$f origin/$SOURCE:$f > $OUTDIR/diff_${f//\//_}.log || true
  fi
done

echo "== Результаты сохранены в папку $OUTDIR =="
ls -lh $OUTDIR
